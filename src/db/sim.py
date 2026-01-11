import time
from typing import List, Tuple, Set, Callable, Optional
from dataclasses import dataclass, field

import db
from mod import models
from mod.models import IFnProg, IFnCancel
from util import log

lg = log.get(__name__)

def normalizeDate(dt) -> str:
    if not dt: return ''
    try:
        # Check if it's a datetime object (has microsecond attribute)
        if hasattr(dt, 'microsecond'): return str(dt.replace(microsecond=0))
        else:
            dtStr = str(dt)
            if '.' in dtStr and ('+' in dtStr or dtStr.endswith('Z')):
                beforeDot = dtStr.split('.')[0]
                if '+' in dtStr:
                    timezone = '+' + dtStr.split('+')[-1]
                    return beforeDot + timezone
                elif dtStr.endswith('Z'): return beforeDot + 'Z'
            return dtStr
    except Exception as e: return str(dt) if dt else ''

@dataclass
class SearchInfo:
    asset: Optional[models.Asset] = None
    bseVec: List[float] = field(default_factory=list)
    bseInfos: List[models.SimInfo] = field(default_factory=list)
    simAids: List[int] = field(default_factory=list)
    assets: List[models.Asset] = field(default_factory=list)



def createReporter(doReport: IFnProg) -> Callable[[str], Tuple[int, int]]:
    def autoReport(msg: str) -> Tuple[int, int]:
        cntAll = db.pics.count()
        cntOk = db.pics.countSimOk(1)
        progress = round(cntOk / cntAll * 100, 2) if cntAll > 0 else 0
        doReport(progress, msg)
        return cntOk, cntAll
    return autoReport


def checkMuodConds(assets: List[models.Asset]) -> bool:
    if not assets or len(assets) < 2: return False
    if not db.dto.muod: return True

    doDate = db.dto.muod_EqDt
    doWidth = db.dto.muod_EqW
    doHeight = db.dto.muod_EqH
    doSize = db.dto.muod_EqFs

    if not any([doDate, doWidth, doHeight, doSize]): return True

    baseAsset = assets[0]
    baseExif = baseAsset.jsonExif
    if not baseExif: return False

    for asset in assets[1:]:
        exif = asset.jsonExif
        if not exif: return False

        if doDate:
            baseDate = str(baseAsset.fileCreatedAt)[:10] if baseAsset.fileCreatedAt else ''
            assetDate = str(asset.fileCreatedAt)[:10] if asset.fileCreatedAt else ''
            if baseDate != assetDate: return False

        if doWidth:
            if baseExif.exifImageWidth != exif.exifImageWidth: return False

        if doHeight:
            if baseExif.exifImageHeight != exif.exifImageHeight: return False

        if doSize:
            if baseExif.fileSizeInByte != exif.fileSizeInByte: return False

    return True


def findCandidate(autoId: int, taskArgs: dict) -> models.Asset:
    asset = None

    if not autoId and taskArgs.get('assetId'):
        lg.info(f"[sim:fnd] search from task args assetId")
        assetId = taskArgs.get('assetId')
        asset = db.pics.getById(assetId)
        if asset: autoId = asset.autoId
    else: asset = db.pics.getByAutoId(autoId) if autoId else None

    if not autoId: raise RuntimeError(f"[tsk] sim.assAid is empty")

    if not asset: raise RuntimeError(f"[sim:fnd] not found asset #{autoId}")

    if asset.simGIDs: raise RuntimeError(f"[sim:fnd] asset #{asset.autoId} already searched, please clear All Records first")

    return asset



def searchBy(src: Optional[models.Asset], doRep: IFnProg, isCancel: IFnCancel, fromUrl: bool=False) -> List[SearchInfo]:
    gis = []
    ass = src
    grpIdx = 1

    skipAids = []

    sizeMax = db.dto.muod_Size

    while len(gis) < sizeMax:
        if isCancel():
            lg.info(f"[sim:sh] user cancelled")
            break

        if not ass:
            nextAss = db.pics.getAnyNonSim(skipAids)
            if not nextAss:
                lg.info(f"[sim:sh] No more assets to search")
                break
            ass = nextAss
            lg.info(f"[sim:sh] while by search NonSim #{ass.autoId}, skips[{skipAids}]")

        prog = int((len(gis) / sizeMax) * 100) if sizeMax > 0 else 0
        doRep(prog, f"Searching group {len(gis) + 1}/{sizeMax} - Asset #{ass.autoId}")

        try:
            gi = findGroupBy(ass, doRep, grpIdx, fromUrl)

            if not gi.assets:
                if fromUrl:
                    lg.info(f"[sim:sh] not found from url #{ass.autoId}")
                    break

                lg.info(f"[sim:sh] group not have any assets..")
                ass = None
                continue

            existingIds = {ast.autoId for grp in gis for ast in grp.assets}
            hasDup = any(ast.autoId in existingIds for ast in gi.assets)
            if hasDup:
                lg.info(f"[sim:sh] group has duplicate autoId, skip to avoid UI confusion")
                skipAids.append(ass.autoId)
                ass = None
                continue

            gis.append(gi)
            lg.info(f"[sim:sh] Found group {len(gis)} with {len(gi.assets)} assets")
            grpIdx += 1

            ass = None
        except Exception as e:
            lg.error(f"[sim:sh] Error processing asset #{ass.autoId}: {e}")
            raise

        # break for normal mode
        if fromUrl or not db.dto.muod: break

    totalAssets = sum(len(g.assets) for g in gis)
    doRep(100, f"Found {len(gis)} groups with {totalAssets} total assets")
    return gis


def findGroupBy(asset: models.Asset, doReport: IFnProg, grpId: int, fromUrl=False) -> SearchInfo:
    lg.info(f"[sim:fg] grpId[{grpId}] #{asset.autoId}")
    result = SearchInfo()
    result.asset = asset

    time.sleep(0.1)
    thMin = db.dto.thMin

    bseVec, bseInfos = db.vecs.findSimiliar(asset.autoId, thMin)
    result.bseVec = bseVec
    result.bseInfos = bseInfos

    if not bseInfos:
        lg.warn(f"[sim:ss] #{asset.autoId} not found any similar, may not store vector")
        db.pics.setVectoredBy(asset, 0)
        return result

    simAids = [i.aid for i in bseInfos if not i.isSelf]

    if db.dto.excl and db.dto.excl_FilNam:
        filteredAids = []
        for aid in simAids:
            simAsset = db.pics.getByAutoId(aid)
            if simAsset and not db.dto.checkIsExclude(simAsset): filteredAids.append(aid)
        simAids = filteredAids
        lg.info(f"[sim:ss] After extension filter: {len(simAids)} similar images remain")

    result.simAids = simAids

    if not simAids:
        lg.info(f"[sim:ss] NoFound #{asset.autoId}")
        db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
        return result

    if db.dto.muod:
        assets = [asset] + [db.pics.getByAutoId(aid) for aid in simAids if db.pics.getByAutoId(aid)]
        if not checkMuodConds(assets):
            lg.info(f"[sim:ss] Group conditions not met for #{asset.autoId}")
            db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
            return result

    if db.dto.excl and db.dto.excl_FndLes > 0:
        if len(simAids) < db.dto.excl_FndLes:
            lg.info(f"[sim:ss] Excluding #{asset.autoId}, similar count({len(simAids)}) < threshold({db.dto.excl_FndLes})")
            db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
            return result

    rootGID = asset.autoId
    db.pics.setSimGIDs(asset.autoId, rootGID)
    db.pics.setSimInfos(asset.autoId, bseInfos)

    processChildren(asset, bseInfos, simAids, doReport)

    if not fromUrl and db.dto.muod:
        #not fromUrl and enable muod
        assets = db.pics.getSimAssets(asset.autoId, False) # muod group ignore rtree
        for i, ass in enumerate(assets):
            ass.vw.muodId = grpId
            ass.vw.isMain = (i == 0)

        lg.info(f"[sim:fnd] Found group {grpId} with {len(assets)} assets")
        result.assets = assets
    else: result.assets = db.pics.getSimAssets(asset.autoId, db.dto.rtree)

    return result


def processChildren(asset: models.Asset, bseInfos: List[models.SimInfo], simAids: List[int], doReport: IFnProg) -> Set[int]:
    thMin = db.dto.thMin
    maxItems = db.dto.rtreeMax


    rootGID = asset.autoId
    db.pics.setSimGIDs(asset.autoId, rootGID)
    db.pics.setSimInfos(asset.autoId, bseInfos)

    doneIds = {asset.autoId}
    simQ = [(aid, 0) for aid in simAids]

    while simQ:
        aid, depth = simQ.pop(0)
        if aid in doneIds: continue

        doneIds.add(aid)
        doReport(50, f"Processing children similar photo #{aid} depth({depth}) count({len(doneIds)})")

        try:
            ass = db.pics.getByAutoId(aid)
            if ass.simOk: continue  # ignore already resolved

            lg.info(f"[sim:fnd] search child #{aid} depth[{depth}]items({len(doneIds)}/{maxItems})")
            cVec, cInfos = db.vecs.findSimiliar(aid, thMin)

            db.pics.setSimGIDs(aid, rootGID)
            db.pics.setSimInfos(aid, cInfos)

            # Add children to queue if haven't reached max depth/items
            if len(doneIds) < maxItems:
                for inf in cInfos:
                    if inf.aid not in doneIds: simQ.append((inf.aid, depth + 1))
        except Exception as ce: raise RuntimeError(f"Error processing similar image {aid}: {ce}")

        # Check item limit
        if len(doneIds) >= maxItems:
            lg.warn(f"[sim:fnd] Reached max items limit ({maxItems}), stopping search..")
            doReport(90, f"Reached max items limit ({maxItems}), processing current item...")
            break

    return doneIds



def getAutoSelectAuids(src: List[models.Asset]) -> List[int]:
    lg.info(f"[ausl] Starting auto-selection, auSelEnable[{db.dto.ausl}], assets count={len(src) if src else 0}")
    lg.info(f"[ausl] Weights: Earlier[{db.dto.ausl_Earlier}] Later[{db.dto.ausl_Later}] ExifRich[{db.dto.ausl_ExRich}] ExifPoor[{db.dto.ausl_ExPoor}] BigSize[{db.dto.ausl_OfsBig}] SmallSize[{db.dto.ausl_OfsSml}] BigDim[{db.dto.ausl_DimBig}] SmallDim[{db.dto.ausl_DimSml}] HighSim[{db.dto.ausl_SkipLow}] AlwaysPickLivePhoto[{db.dto.ausl_AllLive}] jpg[{db.dto.ausl_TypJpg}] png[{db.dto.ausl_TypPng}] heic[{db.dto.ausl_TypHeic}] fav[{db.dto.ausl_Fav}] inAlb[{db.dto.ausl_InAlb}]")

    if not db.dto.ausl or not src: return []

    active = any([
            db.dto.ausl_Earlier > 0, db.dto.ausl_Later > 0,
            db.dto.ausl_ExRich > 0, db.dto.ausl_ExPoor > 0,
            db.dto.ausl_OfsBig > 0, db.dto.ausl_OfsSml > 0,
            db.dto.ausl_DimBig > 0, db.dto.ausl_DimSml > 0,
            db.dto.ausl_NamLon > 0, db.dto.ausl_NamSht > 0,
            db.dto.ausl_TypJpg > 0, db.dto.ausl_TypPng > 0, db.dto.ausl_TypHeic > 0,
            db.dto.ausl_Fav > 0, db.dto.ausl_InAlb > 0,
        ])

    if not active: return []

    assets = _groupAssetsByCondGroup(src)
    lg.info(f"[ausl] Grouped {len(src)} assets into {len(assets)} groups")

    selIds = []

    for grpId, grpAss in assets.items():
        lg.info(f"[ausl] Processing group {grpId} with {len(grpAss)} assets: {[a.autoId for a in grpAss]}")

        liveIds = _checkAlwaysPickLivePhoto(grpAss, grpId)
        if liveIds:
            selIds.extend(liveIds)
            lg.info(f"[ausl] Group {grpId}: Selected ALL LivePhoto assets {liveIds}")
            continue

        if _shouldSkipGroupBy(grpAss, grpId):
            lg.info(f"[ausl] Group {grpId}: Skipping group due to low similarity photos")
            continue

        bestId = _selectBestAsset(grpAss)
        if bestId:
            selIds.append(bestId)
            lg.info(f"[ausl] Group {grpId}: Selected best weighted asset {bestId}")
        else: lg.warn(f"[ausl] Group {grpId}: No best asset found despite having {len(grpAss)} assets")

    lg.info(f"[ausl] Final selection: {len(selIds)} assets: {selIds}")
    return selIds


def _shouldSkipGroupBy(src: List[models.Asset], grpId: int) -> bool:
    lg.info(f"[ausl] ------ Group[ {grpId} ] assets[ {len(src)} ]------")

    if not db.dto.ausl_SkipLow: return False

    hasLow = False
    ats = []

    for ass in src:
        scr = ass.vw.score
        if scr != 0 and scr <= 0.96:
            hasLow = True
            ats.append(f"#{ass.autoId}({scr})")
            #lg.info(f"[ausl] Group {grpId}: Asset {ass.autoId} has LOW similarity (score={scr} <= 0.96)")

    if hasLow:
        lg.info(f"[ausl] Group {grpId}: SKIPPING group due to low similarity assets: {ats}")
        return True

    #lg.info(f"[ausl] Group {grpId}: All assets have high similarity, processing group")
    return False


def _groupAssetsByCondGroup(src: List[models.Asset]) -> dict:
    lg.info(f"[ausl] Starting grouping for {len(src)} assets")
    rst = {}

    for at in src:
        grpId = at.vw.muodId
        if grpId is None:
            grpId = at.autoId
            lg.debug(f"[ausl] Asset {at.autoId}: No muodId, using autoId as groupId")
        else: lg.debug(f"[ausl] Asset {at.autoId}: Using muodId {grpId}")

        if grpId not in rst: rst[grpId] = []
        rst[grpId].append(at)

    for grpId, grpAss in rst.items():
        assIds = [a.autoId for a in grpAss]
        lg.info(f"[ausl] Group {grpId}: Contains {len(grpAss)} assets: {assIds}")

    return rst



@dataclass
class IMetrics:
    aid: int
    dt: str
    exfCnt: int
    fileSz: int
    dim: int
    nameLen: int
    fileType: str
    isFav: bool
    hasAlb: bool
    ownerId: str


def _selectBestAsset(grpAssets: List[models.Asset]) -> int:
    if not grpAssets: raise RuntimeError("No Group")

    def countExif(exif) -> int:
        if not exif: return 0

        fields = [
            'dateTimeOriginal', 'modifyDate', 'make', 'model', 'lensModel',
            'fNumber', 'focalLength', 'exposureTime', 'iso',
            'latitude', 'longitude', 'city', 'state', 'country', 'description',
            'exifImageWidth', 'exifImageHeight', 'fileSizeInByte'
        ]

        return sum(1 for f in fields if hasattr(exif, f) and getattr(exif, f, None) is not None)

    def collectMetrics(assets: List[models.Asset]) -> List[IMetrics]:
        metrics = []
        for ass in assets:
            dt = None
            if ass.jsonExif: dt = ass.jsonExif.dateTimeOriginal or ass.fileCreatedAt

            exfCnt = countExif(ass.jsonExif) if ass.jsonExif else 0
            fileSz = ass.jsonExif.fileSizeInByte if ass.jsonExif and ass.jsonExif.fileSizeInByte else 0

            dim = 0
            if ass.jsonExif:
                w = ass.jsonExif.exifImageWidth or 0
                h = ass.jsonExif.exifImageHeight or 0
                dim = w + h

            nameLen = len(ass.originalFileName) if ass.originalFileName else 0

            fileType = ''
            if ass.originalFileName: fileType = ass.originalFileName.lower().split('.')[-1] if '.' in ass.originalFileName else ''

            ndt = normalizeDate(dt)
            isFav = bool(ass.isFavorite)
            hasAlb = bool(ass.ex and ass.ex.albs)
            ownerId = ass.ownerId or ''
            metrics.append(IMetrics(aid=ass.autoId, dt=ndt, exfCnt=exfCnt, fileSz=fileSz, dim=dim, nameLen=nameLen, fileType=fileType, isFav=isFav, hasAlb=hasAlb, ownerId=ownerId))
        return metrics

    def calcScore(idx: int, met: List[IMetrics]) -> Tuple[int, List[str]]:
        score = 0
        details = []

        def addScore(weight: int, vals: List, isMax: bool, label: str):
            nonlocal score, details
            if weight > 0 and len(set(vals)) > 1:
                target = max(vals) if isMax else min(vals)
                if vals[idx] == target:
                    pts = weight * 10
                    score += pts
                    details.append(f"{label}+{pts}")

        dates = [m.dt for m in met]
        validDates = [d for d in dates if d]

        if dates[idx] and validDates and len(set(validDates)) > 1:
            if db.dto.ausl_Earlier > 0 and dates[idx] == min(validDates):
                pts = db.dto.ausl_Earlier * 10
                score += pts
                details.append(f"Earlier+{pts}")
            if db.dto.ausl_Later > 0 and dates[idx] == max(validDates):
                pts = db.dto.ausl_Later * 10
                score += pts
                details.append(f"Later+{pts}")

        addScore(db.dto.ausl_ExRich, [m.exfCnt for m in met], True, "ExifRich")
        addScore(db.dto.ausl_ExPoor, [m.exfCnt for m in met], False, "ExifPoor")
        addScore(db.dto.ausl_OfsBig, [m.fileSz for m in met], True, "BigSize")
        addScore(db.dto.ausl_OfsSml, [m.fileSz for m in met], False, "SmallSize")
        addScore(db.dto.ausl_DimBig, [m.dim for m in met], True, "BigDim")
        addScore(db.dto.ausl_DimSml, [m.dim for m in met], False, "SmallDim")
        addScore(db.dto.ausl_NamLon, [m.nameLen for m in met], True, "LongName")
        addScore(db.dto.ausl_NamSht, [m.nameLen for m in met], False, "ShortName")

        if db.dto.ausl_TypJpg > 0 and met[idx].fileType in ['jpg', 'jpeg']:
            pts = db.dto.ausl_TypJpg * 10
            score += pts
            details.append(f"JPG+{pts}")
        if db.dto.ausl_TypPng > 0 and met[idx].fileType == 'png':
            pts = db.dto.ausl_TypPng * 10
            score += pts
            details.append(f"PNG+{pts}")
        if db.dto.ausl_TypHeic > 0 and met[idx].fileType in ['heic', 'heif']:
            pts = db.dto.ausl_TypHeic * 10
            score += pts
            details.append(f"HEIC+{pts}")

        if db.dto.ausl_Fav > 0 and met[idx].isFav:
            pts = db.dto.ausl_Fav * 10
            score += pts
            details.append(f"Fav+{pts}")
        if db.dto.ausl_InAlb > 0 and met[idx].hasAlb:
            pts = db.dto.ausl_InAlb * 10
            score += pts
            details.append(f"InAlb+{pts}")

        usrPar = db.dto.asul_Usr or ''
        if usrPar and ':' in usrPar:
            parts = usrPar.split(':')
            uid = parts[0]
            sco = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            if sco > 0 and met[idx].ownerId == uid:
                pts = sco * 10
                score += pts
                details.append(f"Owner+{pts}")

        return score, details

    met = collectMetrics(grpAssets)

    lg.info(f"[ausl] Group comparison:")
    for m in met: lg.info(f"[ausl]   #{m.aid}: date[{m.dt}] exif[{m.exfCnt}] fsize[{m.fileSz}] dim[{m.dim}] name[{m.nameLen}] fav[{m.isFav}] alb[{m.hasAlb}] owner[{m.ownerId[:8] if m.ownerId else ''}]")

    bestAss = None
    bestScr = -1

    for i, ass in enumerate(grpAssets):
        scr, det = calcScore(i, met)
        lg.info(f"[ausl] #{ass.autoId}: score[{scr}] ({', '.join(det) if det else 'no matches'})")

        if scr > bestScr:
            bestScr = scr
            bestAss = ass

    if not bestAss: raise RuntimeError("NotFound best Asset")
    return bestAss.autoId



def _checkAlwaysPickLivePhoto(grpAssets: List[models.Asset], grpId: int) -> List[int]:
    if not db.dto.ausl_AllLive: return []

    liveIds = []
    for ass in grpAssets:
        hasCID = ass.vdoId is not None
        hasPath = ass.pathVdo

        if hasCID or hasPath:
            liveIds.append(ass.autoId)
            lg.info(f"[ausl] Group {grpId}: Found LivePhoto asset {ass.autoId} (CID={hasCID}, Path={bool(hasPath)})")

    if not liveIds: return []

    lg.info(f"[ausl] Group {grpId}: Selecting ALL {len(liveIds)} LivePhoto assets: {liveIds}")
    return liveIds
