import time
from collections import defaultdict
from typing import List, Tuple, Set, Callable, Optional
from dataclasses import dataclass, field

import db
from mod import models
from mod.models import IFnProg, IFnCancel
from util import log

lg = log.get(__name__)

@dataclass
class BatchStats:
	groups: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))

	def add(self, aid: int, result: str): self.groups[result].append(aid)

	def flush(self, batchN: int, qdrantMs: int, aidLo: int, aidHi: int):
		parts = []
		for k in ('found', 'dupSkip', 'noFound'):
			aids = self.groups.get(k)
			if not aids: continue
			if k in ('found', 'dupSkip'): parts.append(f"{k}[{','.join('#'+str(a) for a in aids)}]")
			else: parts.append(f"{k}({len(aids)})")
		for k, aids in self.groups.items():
			if k in ('found', 'dupSkip', 'noFound'): continue
			parts.append(f"{k}({len(aids)})")
		lg.info(f"[sim:bat] cnt[{batchN}] qdrant[{qdrantMs}ms] aids[#{aidLo}~#{aidHi}] {' '.join(parts)}")

@dataclass
class SearchInfo:
	asset: Optional[models.Asset] = None
	bseInfos: List[models.SimInfo] = field(default_factory=list)
	simAids: List[int] = field(default_factory=list)
	assets: List[models.Asset] = field(default_factory=list)
	result: Optional[str] = None

@dataclass
class SearchResult:
	groups: List[SearchInfo] = field(default_factory=list)
	corrupted: List[int] = field(default_factory=list)



def createReporter(doReport: IFnProg) -> Callable[[str], Tuple[int, int]]:
	def autoReport(msg: str) -> Tuple[int, int]:
		cntAll = db.pics.count()
		cntOk = db.pics.countSimOk(1)
		progress = round(cntOk / cntAll * 100, 2) if cntAll > 0 else 0
		doReport(progress, msg)
		return cntOk, cntAll
	return autoReport


def checkGroupConds(assets: List[models.Asset]) -> Tuple[bool, str]:
	if not assets or len(assets) < 2: return False, "len<2"

	doDate = db.dto.gpsk.eqDt
	doWidth = db.dto.gpsk.eqW
	doHeight = db.dto.gpsk.eqH
	doSize = db.dto.gpsk.eqFsz

	if not any([doDate, doWidth, doHeight, doSize]): return True, ""

	baseAsset = assets[0]
	baseExif = baseAsset.jsonExif
	if not baseExif: return False, "noExif"

	for asset in assets[1:]:
		exif = asset.jsonExif
		if not exif: return False, "noExif"

		if doDate:
			baseDate = str(baseAsset.fileCreatedAt)[:10] if baseAsset.fileCreatedAt else ''
			assetDate = str(asset.fileCreatedAt)[:10] if asset.fileCreatedAt else ''
			if baseDate != assetDate: return False, "dt"

		if doWidth:
			if baseExif.exifImageWidth != exif.exifImageWidth: return False, "w"

		if doHeight:
			if baseExif.exifImageHeight != exif.exifImageHeight: return False, "h"

		if doSize:
			if baseExif.fileSizeInByte != exif.fileSizeInByte: return False, "fsz"

	return True, ""


def isOverlap(grps:List[List[models.Asset]],assets:List[models.Asset])->bool:
	used = {a.autoId for g in grps for a in g if not a.isKep}
	return any(a.autoId in used for a in assets if not a.isKep)


def loadGrps(rootAids:List[int],incGroup:bool,mx:int)->List[List[models.Asset]]:
	grps:List[List[models.Asset]]=[]
	for aid in rootAids:
		if len(grps)>=mx:break
		assets=db.pics.getSimAssets(aid,incGroup)
		if isOverlap(grps,assets):continue
		for ass in assets:ass.vw.muodId=len(grps)+1
		grps.append(assets)
	return grps


def findCandidate(autoId:int,taskArgs:dict)->models.Asset:
	asset = None

	if not autoId and taskArgs.get('assetId'):
		# lg.info(f"[sim:fnd] search from task args assetId")
		assetId = taskArgs.get('assetId')
		asset = db.pics.getById(assetId)
		if asset: autoId = asset.autoId
	else: asset = db.pics.getByAutoId(autoId) if autoId else None

	if not autoId: raise RuntimeError(f"[tsk] sim.assAid is empty")
	if not asset: raise RuntimeError(f"[sim:fnd] not found asset #{autoId}")

	if db.pics.hasSimGIDs(asset.autoId): raise RuntimeError(f"[sim:fnd] asset #{asset.autoId} already searched, please clear All Records first")

	return asset




def searchBy(src:models.Asset, doRep:IFnProg, isCancel:IFnCancel, fromUrl=False, BatchSize=128) -> SearchResult:
	gis = []
	grpIdx = 1
	skipAids = []
	corrupted: list[int] = []
	sizeMax = (db.dto.muod.sz or 1) if not fromUrl else 1 #when fromUrl only process one
	thMin = db.dto.thMin
	lg.info(f"[sim:sh] sz[{db.dto.muod.sz}] sizeMax[{sizeMax}] url[{fromUrl}] batch[{BatchSize}]")

	pending: list[models.Asset] = [src] if src else []
	stopUrl = False

	while len(gis) < sizeMax and not stopUrl:
		if isCancel():
			lg.info(f"[sim:sh] user cancelled")
			break

		if not pending:
			pending = db.pics.getAnyNonSim(skipAids, limit=BatchSize)
			if not pending:
				lg.info(f"[sim:sh] No more assets to search")
				break

		aids = [a.autoId for a in pending]
		aidLo, aidHi = min(aids), max(aids)
		t0 = time.time()
		simMap = db.vecs.findSimiliar(aids, thMin)
		batchMs = int((time.time() - t0) * 1000)

		stats = BatchStats()
		processed = 0
		for ass in pending:
			processed += 1
			if isCancel(): break
			if len(gis) >= sizeMax: break

			sinfo = simMap[ass.autoId]

			if not sinfo:
				db.pics.setVectoredBy([ass], done=0)
				try: db.vecs.deleteBy([ass.autoId])
				except Exception as ce: lg.warn(f"[sim:sh] qdrant clean failed aid[{ass.autoId}]: {ce}")
				corrupted.append(ass.autoId)
				stats.add(ass.autoId, "corrupted")
				lg.warn(f"[sim:sh] aid[{ass.autoId}] idx corrupted, cleared")
				continue

			prog = int((len(gis) / sizeMax) * 100) if sizeMax > 0 else 0
			doRep(prog, f"Searching group {len(gis) + 1}/{sizeMax} - Asset #{ass.autoId}")

			try:
				gi = findGroupBy(ass, sinfo, doRep, grpIdx, fromUrl, corrupted)

				if not gi.assets:
					if fromUrl:
						stats.add(ass.autoId, "notFoundFromUrl")
						stopUrl = True
						break
					stats.add(ass.autoId, gi.result or "noFound")
					continue

				if isOverlap([g.assets for g in gis],gi.assets):
					stats.add(ass.autoId, "dupSkip")
					skipAids.append(ass.autoId)
					continue

				gis.append(gi)
				stats.add(ass.autoId, "found")
				grpIdx += 1

				if fromUrl or not db.dto.muod.on: break
			except Exception as e:
				lg.error(f"[sim:sh] Error processing asset #{ass.autoId}: {e}")
				raise

		stats.flush(processed, batchMs, aidLo, aidHi)

		pending = pending[processed:]

		if fromUrl: break
		if not db.dto.muod.on and gis: break

	totalAssets = sum(len(g.assets) for g in gis)
	if corrupted: lg.warn(f"[sim:sh] {len(corrupted)} assets corrupted: {corrupted}")
	doRep(100, f"Found {len(gis)} groups with {totalAssets} total assets")
	return SearchResult(groups=gis, corrupted=corrupted)


def dropExcl(infos: List[models.SimInfo]) -> List[models.SimInfo]:
	if not db.dto.excl.on or not db.dto.excl.filNam: return infos

	kept = []
	for info in infos:
		if info.isSelf:
			kept.append(info)
			continue
		simAsset = db.pics.getByAutoId(info.aid)
		if simAsset and not db.dto.checkIsExclude(simAsset): kept.append(info)
	return kept


def findGroupBy(ast: models.Asset, sinfo: List[models.SimInfo], doReport: IFnProg, grpId:int,fromUrl:bool,corrupted:list[int])->SearchInfo:
	sinfo = dropExcl(sinfo)

	rst = SearchInfo()
	rst.asset = ast
	rst.bseInfos = sinfo

	simAids = [i.aid for i in sinfo if not i.isSelf]

	rst.simAids = simAids

	if not simAids:
		db.pics.setSimInfos(ast.autoId, sinfo, isOk=1)
		rst.result = "noFound"
		return rst

	assets = [ast] + [db.pics.getByAutoId(aid) for aid in simAids if db.pics.getByAutoId(aid)]
	condOk, condReason = checkGroupConds(assets)
	if not condOk:
		db.pics.setSimInfos(ast.autoId, sinfo, isOk=1)
		rst.result = f"cond({condReason})"
		return rst

	if db.dto.excl.on and db.dto.excl.fndLes > 0:
		if len(simAids) < db.dto.excl.fndLes:
			db.pics.setSimInfos(ast.autoId, sinfo, isOk=1)
			rst.result = f"excl<{db.dto.excl.fndLes}"
			return rst

	if db.dto.excl.on and db.dto.excl.fndOvr > 0:
		if len(simAids) > db.dto.excl.fndOvr:
			db.pics.setSimInfos(ast.autoId, sinfo, isOk=1)
			rst.result = f"excl>{db.dto.excl.fndOvr}"
			return rst

	rootGID = ast.autoId
	db.pics.setSimGIDs(ast.autoId, rootGID)
	db.pics.setSimInfos(ast.autoId, sinfo)

	processChildren(ast, sinfo, simAids, doReport, corrupted)

	if not fromUrl and db.dto.muod.on:
		assets = db.pics.getSimAssets(ast.autoId, False)
		for i, ass in enumerate(assets):
			ass.vw.muodId = grpId
			ass.vw.isMain = (i == 0)
		rst.assets = assets
	else: rst.assets = db.pics.getSimAssets(ast.autoId, db.dto.rtree)

	if db.dto.pathFilter and rst.assets:
		hasMatch = any(db.dto.pathFilter in (a.originalPath or '') for a in rst.assets)
		if not hasMatch:
			db.pics.setSimInfos(ast.autoId, sinfo, isOk=1)
			rst.assets = []
			rst.result = "pathFil"

	return rst


def processChildren(ast: models.Asset, infos: List[models.SimInfo], simAids: List[int], doReport:IFnProg,corrupted:list[int])->Set[int]:
	thMin = db.dto.thMin
	maxItems = db.dto.rtreeMax

	rootGID = ast.autoId
	db.pics.setSimGIDs(ast.autoId, rootGID)
	db.pics.setSimInfos(ast.autoId, infos)

	doneIds = {ast.autoId}
	layer: list[int] = list(simAids)
	depth = 0

	while layer:
		validAss: list[models.Asset] = []
		for aid in layer:
			if aid in doneIds: continue
			try: ass = db.pics.getByAutoId(aid)
			except Exception as ce: raise RuntimeError(f"Error processing similar image {aid}: {ce}")
			if not ass:
				doneIds.add(aid)
				continue
			doneIds.add(aid)
			if ass.simOk: continue
			validAss.append(ass)
			if len(doneIds) >= maxItems: break

		if not validAss: break

		doReport(50, f"Processing children depth({depth}) count({len(doneIds)}/{maxItems})")

		valid = [a.autoId for a in validAss]
		try: childMap = db.vecs.findSimiliar(valid, thMin)
		except Exception as ce: raise RuntimeError(f"Error batch finding children: {ce}")

		nextLayer: list[int] = []
		for ass in validAss:
			aid = ass.autoId
			cInfos = childMap[aid]
			if not cInfos:
				db.pics.setVectoredBy([ass], done=0)
				try: db.vecs.deleteBy([aid])
				except Exception as ce: lg.warn(f"[sim:children] qdrant clean failed aid[{aid}]: {ce}")
				corrupted.append(aid)
				lg.warn(f"[sim:children] aid[{aid}] idx corrupted, cleared")
				continue

			cInfos = dropExcl(cInfos)

			db.pics.setSimGIDs(aid, rootGID)
			db.pics.setSimInfos(aid, cInfos)

			if len(doneIds) < maxItems:
				for inf in cInfos:
					if inf.aid not in doneIds: nextLayer.append(inf.aid)

		layer = nextLayer
		depth += 1

		if len(doneIds) >= maxItems:
			lg.warn(f"[sim:fnd] Reached max items limit ({maxItems}), stopping search..")
			doReport(90, f"Reached max items limit ({maxItems}), processing current item...")
			break

	return doneIds
