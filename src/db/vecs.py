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

keyColl = "deduper"

conn: Optional[QdrantClient] = None


def init():
    global conn
    try:
        conn = QdrantClient(envs.qdrantUrl, timeout=60)

        create()
    except Exception as e:
        raise mkErr(f"Failed to initialize Qdrant", e)

def close():
    global conn
    try:
        if conn is not None: conn.close()
        conn = None
        return True
    except Exception as e:
        raise mkErr(f"Failed to close database connection", e)


def create():
    try:
        if not conn: raise RuntimeError( "[qdrant] not connection" )
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

            if not conn.collection_exists(keyColl):
                raise RuntimeError(f"[qdrant] Failed to create collection {keyColl}")

            lg.info(f"[qdrant] create successfully, coll[{keyColl}]")

    except Exception as e:
        raise mkErr(f"Failed to initialize Qdrant", e)


def cleanAll():
    try:
        if conn is None: raise RuntimeError("[qdrant] not connection")

        exist = conn.collection_exists(keyColl)

        if exist:
            lg.info(f"[qdrant] Start Clear coll[{keyColl}]..")
            conn.delete_collection(keyColl, 60 * 5)
            lg.info(f"[qdrant] coll[{keyColl}] deleted")

        create()

    except Exception as e:
        raise mkErr(f"[qdrant] Failed to clear vector database", e)


def count():
    try:
        if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

        rst = conn.count(collection_name=keyColl)
        return rst.count
    except Exception as e:
        raise mkErr(f"Error checking database population", e)


def deleteBy(aids: list[int]):
    try:
        if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

        rst = conn.delete(
            collection_name=keyColl,
            points_selector=qmod.PointIdsList(points=aids) # type: ignore
        )

        lg.info(f"[vec] delete status[{rst}] count[ {len(aids)} ]")
        if rst.status != qmod.UpdateStatus.COMPLETED:
            raise RuntimeError(f"Delete operation failed with status: {rst.status}")


    except Exception as e:
        raise mkErr(f"Error deleting vector for asset {aids}", e)


def save(aid: int, vector: np.ndarray, confirm=True):
    try:
        if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

        if not isinstance(vector, np.ndarray):
            raise ValueError(f"[vecs] Vector must be numpy array, got {type(vector)}")

        if np.isnan(vector).any():
            raise ValueError(f"[vecs] Vector contains NaN values")

        if np.isinf(vector).any():
            raise ValueError(f"[vecs] Vector contains infinite values")

        vecList = vector.tolist()
        if not vecList or len(vecList) != 2048:
            raise ValueError(f"[vecs] Vector length is incorrect, expected 2048, actual {len(vecList) if vecList else 0}")

        if not all(isinstance(x, (int, float)) for x in vecList[:5]):
            raise ValueError(f"[vecs] Vector contains invalid data types")

        conn.upsert(
            collection_name=keyColl,
            points=[qmod.PointStruct(id=aid, vector=vecList, payload={"aid": aid})]
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

    except Exception as e:
        raise mkErr(f"Error saving vector for asset {aid}", e)


def getBy(aid: int) -> List[float]:
    try:
        if conn is None: raise RuntimeError("[vecs] Qdrant connection not initialized")

        dst = conn.retrieve(
            collection_name=keyColl,
            ids=[aid],
            with_payload=True, with_vectors=True
        )

        if not dst: raise RuntimeError(f"[vecs] Vector for asset aid[{aid}] does not exist")

        if not hasattr(dst[0], 'vector') or dst[0].vector is None:
            raise RuntimeError(f"[vecs] Vector for asset aid[{aid}] is empty")

        vector = dst[0].vector

        # lg.info(f"Original vector data type: {type(vector)}")

        if isinstance(vector, np.ndarray):
            raise RuntimeError(f"[vecs] Vector is a NumPy array, converting to list")
        if hasattr(vector, 'tolist') and callable(getattr(vector, 'tolist')):
            raise RuntimeError(f"[vecs] Vector has tolist method, attempting conversion")

        if not hasattr(vector, '__len__') or len(vector) == 0:
            raise RuntimeError(f"[vecs] Vector format for asset aid[{aid}] is incorrect: {type(vector)}")

        if not isinstance(vector, list):
            raise RuntimeError(f"[vecs] Vector not a list: {type(vector)}")

        return vector #type:ignore

    except Exception as e:
        raise mkErr(f"[vecs] Error get asset vector aid[{aid}]", e)


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
                if isinstance(point.vector, list) and len(point.vector) > 0:
                    result[int(point.id)] = point.vector
                else:
                    lg.warn(f"[vecs] Invalid vector format for aid[{point.id}]: {type(point.vector)}")
            else:
                lg.warn(f"[vecs] Missing vector for aid[{point.id}]")

        lg.info(f"[vecs] getBatch: successfully retrieved {len(result)}/{len(aids)} vectors")
        return result

    except Exception as e:
        raise mkErr(f"[vecs] Error batch getting vectors for aids{aids}", e)


def search(vec, thMin: float = 0.95, limit=100) -> list[qdrant_client.http.models.ScoredPoint]:
    try:
        if conn is None: raise RuntimeError("Qdrant connection not initialized")

        # distance = qmod.Distance.COSINE if method == ks.use.mth.cosine else qmod.Distance.EUCLID

        # if thMin >= 0.97: thMin = 0.95

        rep = conn.query_points(collection_name=keyColl, query=vec, limit=limit, score_threshold=thMin, with_payload=True)
        rst = rep.points

        return rst

    except Exception as e:
        raise mkErr(f"[vecs] Error searching {vec}", e)


#------------------------------------------------------------------------
# only return different id
#------------------------------------------------------------------------
def findSimiliar(aid: int, thMin: float = 0.95, limit=100, logRow = False) -> Tuple[list[float], list[models.SimInfo]]:
    try:
        if conn is None: raise RuntimeError("Qdrant connection not initialized")

        vector = getBy(aid)

        rep = conn.query_points(collection_name=keyColl, query=vector, limit=limit, score_threshold=thMin, with_payload=True)
        rst = rep.points
        infos: list[models.SimInfo] = []

        lg.info(f"[vecs:find] #{aid}, threshold[{thMin}-1.0] limit[{limit}] found[{len(rst)}]")
        for i, hit in enumerate(rst):
            hit_aid = int(hit.id)
            if logRow: lg.info(f"\tno.{i + 1}: AID[{hit_aid}], score[{hit.score:.6f}] self[{int(hit.id) == aid}]")

            if hit.score <= 1.0 or hit_aid == aid:  #always add self
                isSelf = hit_aid == aid
                infos.append(models.SimInfo(hit_aid, hit.score, isSelf))

        return vector, infos
    except Exception as e:
        raise mkErr(f"Error finding similar assets for aid[{aid}]", e)
