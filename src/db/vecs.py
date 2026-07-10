from typing import List, Optional, Tuple
import numpy as np
import qdrant_client.http.models
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmod

from conf import envs
from util import log
from mod import models
from util.err import mkErr


lg = log.get(__name__)

keyColl = envs.qdrantColl

conn: Optional[QdrantClient] = None


def init():
	global conn
	try:
		conn = QdrantClient(envs.qdrantUrl, timeout=60)

		create()
	except Exception as e: raise mkErr(f"Failed to initialize Qdrant", e)

def close():
	global conn
	try:
		if conn is not None: conn.close()
		conn = None
		return True
	except Exception as e: raise mkErr(f"Failed to close database connection", e)


def create():
	try:
		if not conn: raise RuntimeError("[qdrant] not connection")
		if not conn.collection_exists(keyColl):
			lg.info(f"[qdrant] creating coll[{keyColl}]...")
			conn.create_collection(
				collection_name=keyColl,
				vectors_config=qmod.VectorParams(
					size=2048,
					distance=qmod.Distance.COSINE
				),
				timeout=60
			)

			if not conn.collection_exists(keyColl): raise RuntimeError(f"[qdrant] Failed to create collection {keyColl}")

			lg.info(f"[qdrant] create successfully, coll[{keyColl}]")
	except Exception as e: raise mkErr(f"Failed to initialize Qdrant", e)


def cleanAll():
	try:
		if conn is None: raise RuntimeError("[qdrant] not connection")

		exist = conn.collection_exists(keyColl)

		if exist:
			lg.info(f"[qdrant] Start Clear coll[{keyColl}]..")
			conn.delete_collection(keyColl, 60 * 5)
			lg.info(f"[qdrant] coll[{keyColl}] deleted")

		create()
	except Exception as e: raise mkErr(f"[qdrant] Failed to clear vector database", e)


def count():
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

		rst = conn.count(collection_name=keyColl)
		return rst.count
	except Exception as e: raise mkErr(f"Error checking database population", e)


def getNoUuidAids() -> set[int]:
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

		flt = qmod.Filter(must=[qmod.IsEmptyCondition(is_empty=qmod.PayloadField(key="uuid"))])
		found: set[int] = set()
		offset = None
		page = 0
		while True:
			points, nxt = conn.scroll(
				collection_name=keyColl,
				scroll_filter=flt,
				limit=2000,
				with_payload=False, with_vectors=False,
				offset=offset,
			)
			for p in points: found.add(int(p.id))
			page += 1
			lg.info(f"[vecs] getNoUuidAids page[{page}] cnt[{len(points)}] total[{len(found)}]")
			if nxt is None: break
			offset = nxt
		return found
	except Exception as e: raise mkErr(f"[vecs] Error scanning no-uuid points", e)


def setUuidPayloads(pairs: list[tuple[int, str]], bsz=500) -> int:
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")
		if not pairs: return 0

		total = len(pairs)
		done = 0
		for i in range(0, total, bsz):
			chunk = pairs[i:i + bsz]
			ops = [
				qmod.SetPayloadOperation(set_payload=qmod.SetPayload(payload={"uuid": uid}, points=[aid]))
				for aid, uid in chunk
			]
			isLast = i + bsz >= total
			conn.batch_update_points(
				collection_name=keyColl, update_operations=ops,
				wait=isLast, ordering=qmod.WriteOrdering.WEAK,
			)
			done += len(chunk)
			lg.info(f"[vecs] setUuidPayloads batch[{i // bsz + 1}] done[{done}/{total}]")
		return done
	except Exception as e: raise mkErr(f"[vecs] Error setting uuid payloads", e)


def deleteBy(aids: list[int]):
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

		rst = conn.delete(
			collection_name=keyColl,
			points_selector=qmod.PointIdsList(points=aids) # type: ignore
		)

		lg.info(f"[vec] delete status[{rst}] count[ {len(aids)} ]")
		if rst.status != qmod.UpdateStatus.COMPLETED: raise RuntimeError(f"Delete operation failed with status: {rst.status}")
	except Exception as e: raise mkErr(f"Error deleting vector for asset {aids}", e)


def save(aid: int, vector: np.ndarray, uuid: str, confirm=True):
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

		# if not isinstance(vector, np.ndarray): raise ValueError(f"[vecs] Vector must be numpy array, got {type(vector)}")

		if np.isnan(vector).any(): raise ValueError(f"[vecs] Vector contains NaN values")

		if np.isinf(vector).any(): raise ValueError(f"[vecs] Vector contains infinite values")

		vecList = vector.tolist()
		if not vecList or len(vecList) != 2048: raise ValueError(f"[vecs] Vector length is incorrect, expected 2048, actual {len(vecList) if vecList else 0}")

		if not all(isinstance(x, (int, float)) for x in vecList[:5]): raise ValueError(f"[vecs] Vector contains invalid data types")

		conn.upsert(
			collection_name=keyColl,
			points=[qmod.PointStruct(id=aid, vector=vecList, payload={"aid": aid, "uuid": uuid})]
		)

		if confirm:
			try:
				stored = conn.retrieve(
					collection_name=keyColl,
					ids=[aid], with_vectors=True
				)
				if not stored: raise RuntimeError(f"[vecs] Failed save vector aid[{aid}]")
				if not hasattr(stored[0], 'vector') or stored[0].vector is None: raise RuntimeError(f"[vecs] Stored vector is null aid[{aid}]")
			except Exception as ve:
				lg.error(f"Error validating vector storage: {str(ve)}")
				raise
	except Exception as e: raise mkErr(f"Error saving vector for asset {aid}", e)


def getVec(aid: int) -> List[float]:
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

		dst = conn.retrieve(
			collection_name=keyColl,
			ids=[aid],
			with_payload=True, with_vectors=True
		)

		if not dst: raise RuntimeError(f"[vecs] Vector for asset aid[{aid}] does not exist")

		if not hasattr(dst[0], 'vector') or dst[0].vector is None: raise RuntimeError(f"[vecs] Vector for asset aid[{aid}] is empty")

		vec = dst[0].vector

		# lg.info(f"Original vector data type: {type(vector)}")

		if isinstance(vec, np.ndarray): raise RuntimeError(f"[vecs] Vector is a NumPy array, converting to list")
		if hasattr(vec, 'tolist') and callable(getattr(vec, 'tolist')): raise RuntimeError(f"[vecs] Vector has tolist method, attempting conversion")

		if not hasattr(vec, '__len__') or len(vec) == 0: raise RuntimeError(f"[vecs] Vector format for asset aid[{aid}] is incorrect: {type(vec)}")
		if not isinstance(vec, list): raise RuntimeError(f"[vecs] Vector not a list: {type(vec)}")

		return vec #type:ignore
	except Exception as e: raise mkErr(f"[vecs] Error get asset vector aid[{aid}]", e)


def getAllBy(aids: list[int]) -> dict[int, list]:
	try:
		if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")
		if not aids: return {}

		lg.info(f"[vecs] getBatch: fetching {len(aids)} vectors")

		dst = conn.retrieve(
			collection_name=keyColl,
			ids=aids,
			with_payload=True, with_vectors=True
		)

		result = {}
		for point in dst:
			if hasattr(point, 'vector') and point.vector is not None:
				if isinstance(point.vector, list) and len(point.vector) > 0: result[int(point.id)] = point.vector
				else: lg.warn(f"[vecs] Invalid vector format for aid[{point.id}]: {type(point.vector)}")
			else: lg.warn(f"[vecs] Missing vector for aid[{point.id}]")

		lg.info(f"[vecs] getBatch: successfully retrieved {len(result)}/{len(aids)} vectors")
		return result
	except Exception as e: raise mkErr(f"[vecs] Error batch getting vectors for aids{aids}", e)


def search(vec, thMin: float=0.95, limit=100) -> list[qdrant_client.http.models.ScoredPoint]:
	try:
		if conn is None: raise RuntimeError("Qdrant connection not initialized")

		# distance = qmod.Distance.COSINE if method == ks.use.mth.cosine else qmod.Distance.EUCLID

		# if thMin >= 0.97: thMin = 0.95

		rep = conn.query_points(collection_name=keyColl, query=vec, limit=limit, score_threshold=thMin, with_payload=True)
		rst = rep.points

		return rst
	except Exception as e: raise mkErr(f"[vecs] Error searching {vec}", e)


#------------------------------------------------------------------------
# wait for HNSW index build complete (status=green)
# return True if green, False if timeout/cancelled
#------------------------------------------------------------------------
def waitForGreen(timeout:int=600,isCancel=None,doReport=None)->bool:
	if conn is None:raise RuntimeError("[vecs] Qdrant connection not initialized")
	import time
	start=time.time()
	while True:
		if isCancel and isCancel():
			lg.info(f"[vecs:waitForGreen] cancelled")
			return False
		info=conn.get_collection(keyColl)
		st=info.status
		if str(st).endswith("green"):
			lg.info(f"[vecs:waitForGreen] green after {int(time.time() - start)}s indexed={info.indexed_vectors_count}")
			return True
		if time.time()-start>timeout:
			lg.warn(f"[vecs:waitForGreen] timeout after {timeout}s status={st}")
			return False
		if doReport:doReport(0,f"waiting Qdrant index build (status={st})")
		time.sleep(2)


#------------------------------------------------------------------------
# scan all points, repair HNSW index desync
# excludeAids: skip these aids (e.g. this-round newly-added)
# return (scanned, repaired, broken_aids)
#------------------------------------------------------------------------
def scanRepairIdx(doReport=None,isCancel=None,excludeAids:Optional[set[int]]=None)->tuple[int,int,list[int]]:
	if conn is None:raise RuntimeError("[vecs] Qdrant connection not initialized")

	excludeAids=excludeAids or set()
	scanned=0
	repaired=0
	broken:list[int]=[]
	skipped=0
	offset=None
	page=0

	total=count()

	while True:
		if isCancel and isCancel():
			lg.info(f"[vecs:scanRepairIdx] cancelled at scanned={scanned}")
			break

		points,nxt=conn.scroll(
			collection_name=keyColl,limit=500,
			with_payload=True,with_vectors=True,offset=offset,
		)
		if not points:break
		page += 1

		for p in points:
			aid=int(p.id)
			if aid in excludeAids:
				skipped += 1
				continue
			vec=p.vector
			scanned += 1

			selfFlt=qmod.Filter(must=[qmod.HasIdCondition(has_id=[aid])])
			rep=conn.query_points(collection_name=keyColl,query=vec,query_filter=selfFlt,limit=1,with_payload=False)  # type: ignore
			if rep.points:continue

			if repairIdx(aid,vec): # type: ignore
				repaired += 1
			else:
				broken.append(aid)
				try:conn.delete(collection_name=keyColl,points_selector=qmod.PointIdsList(points=[aid]))
				except Exception as e:lg.warn(f"[vecs:scanRepairIdx] delete broken aid[{aid}] failed: {e}")

		if doReport:
			pct=int(scanned/total * 100) if total>0 else 0
			doReport(pct,f"scan idx page[{page}] scanned={scanned}/{total} repaired={repaired} broken={len(broken)} skipped={skipped}")

		lg.info(f"[vecs:scanRepairIdx] page[{page}] scanned={scanned}/{total} repaired={repaired} broken={len(broken)} skipped={skipped}")

		if nxt is None:break
		offset=nxt

	return scanned,repaired,broken


#------------------------------------------------------------------------
# repair HNSW index: delete + re-upsert same vector
#------------------------------------------------------------------------
def repairIdx(aid: int, vec: list) -> bool:
	if conn is None: return False
	try:
		ret = conn.retrieve(collection_name=keyColl, ids=[aid], with_payload=True)
		if not ret: return False
		payload = ret[0].payload
		conn.delete(collection_name=keyColl, points_selector=qmod.PointIdsList(points=[aid]))
		conn.upsert(collection_name=keyColl,points=[qmod.PointStruct(id=aid,vector=vec,payload=payload)],wait=True)
		selfFlt=qmod.Filter(must=[qmod.HasIdCondition(has_id=[aid])])
		rep=conn.query_points(collection_name=keyColl,query=vec,query_filter=selfFlt,limit=1,with_payload=False)
		ok=bool(rep.points)
		if ok: lg.info(f"[vecs] repairIdx aid[{aid}] ok")
		else: lg.error(f"[vecs] repairIdx aid[{aid}] failed")
		return ok
	except Exception as e:
		lg.error(f"[vecs] repairIdx aid[{aid}] error: {e}")
		return False


#------------------------------------------------------------------------
# batch find similar, always include self
# return: {aid: [SimInfo,...]}
#------------------------------------------------------------------------
def findSimiliar(aids: list[int], thMin: float=0.95, limit=100) -> dict[int, list[models.SimInfo]]:
	try:
		if conn is None: raise RuntimeError("Qdrant connection not initialized")
		if not aids: return {}

		vecMap = getAllBy(aids)

		rst: dict[int, list[models.SimInfo]] = {}
		for aid in aids:
			if aid not in vecMap:
				lg.warn(f"[vecs:findSimiliar] aid[{aid}] vec missing in qdrant")
				rst[aid] = []

		items = [(aid, vecMap[aid]) for aid in aids if aid in vecMap]
		if not items: return rst

		reqs = [
			qmod.QueryRequest(query=vec, score_threshold=thMin, limit=limit, with_payload=True)
			for _, vec in items
		]
		reps = conn.query_batch_points(collection_name=keyColl, requests=reqs)

		for (aid, _), rep in zip(items, reps):
			infos: list[models.SimInfo] = []
			for hit in rep.points:
				hit_aid = int(hit.id)
				if hit.score <= 1.0 or hit_aid == aid:
					infos.append(models.SimInfo(hit_aid, hit.score, hit_aid == aid))

			if not any(i.isSelf for i in infos):
				lg.warn(f"[vecs:findSimiliar] aid[{aid}] idx desync, repairing...")
				vec = vecMap[aid]
				if repairIdx(aid, vec):
					reRep = conn.query_points(collection_name=keyColl, query=vec, score_threshold=thMin, limit=limit, with_payload=True)
					infos = []
					for hit in reRep.points:
						hitAid = int(hit.id)
						if hit.score <= 1.0 or hitAid == aid:
							infos.append(models.SimInfo(hitAid, hit.score, hitAid == aid))
					if not any(i.isSelf for i in infos):
						infos.insert(0, models.SimInfo(aid, 1.0, True))
				else:
					lg.error(f"[vecs:findSimiliar] aid[{aid}] repair failed")
					infos = []

			rst[aid] = infos

		return rst
	except Exception as e: raise mkErr(f"Error finding similar assets for aids[{aids}]", e)
