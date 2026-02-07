import time
from typing import List, Tuple, Set, Callable, Optional
from dataclasses import dataclass, field

import db
from mod import models
from mod.models import IFnProg, IFnCancel
from util import log

lg = log.get(__name__)

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


def checkGroupConds(assets: List[models.Asset]) -> bool:
    if not assets or len(assets) < 2: return False

    doDate = db.dto.gpsk.eqDt
    doWidth = db.dto.gpsk.eqW
    doHeight = db.dto.gpsk.eqH
    doSize = db.dto.gpsk.eqFsz

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

    sizeMax = db.dto.muod.sz or 1
    lg.info( f"[sim:sh] muod.sz[{db.dto.muod.sz}] sizeMax[{sizeMax}]")

    while len(gis) < sizeMax:
        if isCancel():
            lg.info(f"[sim:sh] user cancelled")
            break
        lg.info(f"[sim:sh] looping gis[{len(gis)}] < sizeMax[{sizeMax}]")

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
        if fromUrl or not db.dto.muod.on: break

    totalAssets = sum(len(g.assets) for g in gis)
    doRep(100, f"Found {len(gis)} groups with {totalAssets} total assets")
    return gis


def findGroupBy(asset: models.Asset, doReport: IFnProg, grpId: int, fromUrl=False) -> SearchInfo:
    lg.info(f"[sim:fg] grpId[{grpId}] #{asset.autoId}")
    result = SearchInfo()
    result.asset = asset

    thMin = db.dto.thMin

    bseVec, bseInfos = db.vecs.findSimiliar(asset.autoId, thMin)
    result.bseVec = bseVec
    result.bseInfos = bseInfos

    if not bseInfos:
        lg.warn(f"[sim:ss] #{asset.autoId} not found any similar, may not store vector")
        db.pics.setVectoredBy(asset, 0)
        return result

    simAids = [i.aid for i in bseInfos if not i.isSelf]

    if db.dto.excl.on and db.dto.excl.filNam:
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

    assets = [asset] + [db.pics.getByAutoId(aid) for aid in simAids if db.pics.getByAutoId(aid)]
    if not checkGroupConds(assets):
        lg.info(f"[sim:ss] Group conditions not met for #{asset.autoId}")
        db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
        return result

    if db.dto.excl.on and db.dto.excl.fndLes > 0:
        if len(simAids) < db.dto.excl.fndLes:
            lg.info(f"[sim:ss] Excluding #{asset.autoId}, similar count({len(simAids)}) < threshold({db.dto.excl.fndLes})")
            db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
            return result

    if db.dto.excl.on and db.dto.excl.fndOvr > 0:
        if len(simAids) > db.dto.excl.fndOvr:
            lg.info(f"[sim:ss] Excluding #{asset.autoId}, similar count({len(simAids)}) > threshold({db.dto.excl.fndOvr})")
            db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
            return result

    rootGID = asset.autoId
    db.pics.setSimGIDs(asset.autoId, rootGID)
    db.pics.setSimInfos(asset.autoId, bseInfos)

    processChildren(asset, bseInfos, simAids, doReport)

    if not fromUrl and db.dto.muod.on:
        #not fromUrl and enable muod
        assets = db.pics.getSimAssets(asset.autoId, False) # muod group ignore rtree
        for i, ass in enumerate(assets):
            ass.vw.muodId = grpId
            ass.vw.isMain = (i == 0)

        lg.info(f"[sim:fnd] Found group {grpId} with {len(assets)} assets")
        result.assets = assets
    else: result.assets = db.pics.getSimAssets(asset.autoId, db.dto.rtree)

    if db.dto.pathFilter and result.assets:
        hasMatch = any(db.dto.pathFilter in (a.originalPath or '') for a in result.assets)
        if not hasMatch:
            lg.info(f"[sim:fnd] Group #{asset.autoId} filtered out by pathFilter '{db.dto.pathFilter}'")
            db.pics.setSimInfos(asset.autoId, bseInfos, isOk=1)
            result.assets = []

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



