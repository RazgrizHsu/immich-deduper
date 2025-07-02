import json
import sqlite3
from contextlib import contextmanager
from sqlite3 import Cursor
from typing import Optional, List

from conf import envs
from mod import models
from mod.models import BaseDictModel
from util import log
from util.err import mkErr, tracebk
from db import psql

lg = log.get(__name__)

pathDb = envs.mkitData + 'pics.db'


@contextmanager
def mkConn():
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(pathDb, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        yield conn
    finally:
        if conn:
            conn.close()




def init():
    try:
        with mkConn() as conn:
            c = conn.cursor()

            c.execute('''
                Create Table If Not Exists assets (
                    autoId           INTEGER Primary Key AUTOINCREMENT,
                    id               TEXT Unique,
                    ownerId          TEXT,
                    deviceId         TEXT,
                    type             TEXT,
                    originalFileName TEXT,
                    originalPath     TEXT,
                    fileCreatedAt    TEXT,
                    fileModifiedAt   TEXT,
                    localDateTime    TEXT,
                    isFavorite       INTEGER Default 0,
                    isArchived       INTEGER Default 0,

                    vdoId            TEXT,
                    pathThumbnail    TEXT,
                    pathPreview      TEXT,
                    pathVdo          TEXT,
                    jsonExif         TEXT Default '{}',
                    isVectored       INTEGER Default 0,
                    simOk            INTEGER Default 0,
                    simInfos         TEXT Default '[]',
                    simGIDs          TEXT Default '[]'
                )
                ''')

            c.execute('''
                Create Table If Not Exists users (
                    id     TEXT Primary Key,
                    name   TEXT,
                    email  TEXT,
                    apiKey TEXT
                )
                ''')

            # indexes
            c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_autoId_simOk ON assets(autoId, simOk)''')
            c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_isVectored ON assets(isVectored)''')
            c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_simOk ON assets(simOk)''')
            c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_id ON assets(id)''')

            conn.commit()

            lg.info(f"[pics] db connected: {pathDb}")

        return True
    except Exception as e:
        raise mkErr("Failed to initialize pics database", e)


def clearAll():
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("Drop Table If Exists assets")
            c.execute("Drop Table If Exists users")
            conn.commit()
        return init()
    except Exception as e:
        raise mkErr("Failed to clear pics database", e)


def clearBy(usrId):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            sql = "Delete From assets WHERE ownerId = ?"
            c.execute(sql, (usrId,))
            cnt = c.rowcount
            conn.commit()

            lg.info(f"[pics] delete userId[ {usrId} ] assets[ {cnt} ]")
            return cnt
    except Exception as e:
        raise mkErr(f"Failed to delete assets by userId[{usrId}]", e)


def count(usrId=None):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            sql = "Select Count(*) From assets"
            if usrId:
                sql += " Where ownerId = ?"
                c.execute(sql, (usrId,))
            else:
                c.execute(sql)
            cnt = c.fetchone()[0]
            return cnt
    except Exception as e:
        raise mkErr("Failed to get assets count", e)


#========================================================================
# quary
#========================================================================
def getByAutoId(autoId) -> models.Asset:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("Select * From assets Where autoId= ?", (autoId,))
            row = c.fetchone()

            if not row: raise RuntimeError(f"not found aid[{autoId}]")

            asset = models.Asset.fromDB(c, row)
            return asset
    except Exception as e:
        raise mkErr("Failed to get asset by autoId", e)


def getById(assId) -> models.Asset:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("Select * From assets Where id = ?", (assId,))
            row = c.fetchone()
            if not row: raise RuntimeError( f"NotFound id[{assId}]" )
            asset = models.Asset.fromDB(c, row)
            return asset
    except Exception as e:
        raise mkErr("Failed to get asset by id", e)


def getAllByUsrId(usrId: str) -> List[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute(f"Select * From assets Where ownerId = ? ", (usrId,))
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        raise mkErr(f"Failed to get assets by userId[{usrId}]", e)


def getAllByIds(ids: List[str]) -> List[models.Asset]:
    try:
        if not ids: return []
        with mkConn() as conn:
            c = conn.cursor()
            qargs = ','.join(['?' for _ in ids])
            c.execute(f"Select * From assets Where id IN ({qargs})", ids)
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        raise mkErr(f"Failed to get assets by ids[{ids}]", e)


def getAll(count=0) -> list[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            if not count:
                sql = "Select * From assets"
                c.execute(sql)
            else:
                sql = "Select * From assets LIMIT ?"
                c.execute(sql, (count,))
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        raise mkErr("Failed to get all assets", e)


def getAllNonVector() -> list[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            sql = "Select * From assets WHERE isVectored=0"
            c.execute(sql)
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        raise mkErr("Failed to get non-vector assets", e)


#------------------------------------------------------------------------
# paged
#------------------------------------------------------------------------
def countFiltered(usrId="", opts="all", search="", favOnly=False, arcOnly=False, liveOnly=False):
    try:
        cds = []
        pms = []

        if usrId:
            cds.append("ownerId = ?")
            pms.append(usrId)

        if favOnly:
            cds.append("isFavorite = 1")

        if arcOnly:
            cds.append("isArchived = 1")

        if liveOnly:
            cds.append("vdoId IS NOT NULL")

        if opts == "with_vectors":
            cds.append("isVectored = 1")
        elif opts == "without_vectors":
            cds.append("isVectored = 0")

        if search and len(search.strip()) > 0:
            cds.append("originalFileName LIKE ?")
            pms.append(f"%{search}%")

        query = "Select Count(*) From assets"
        if cds: query += " WHERE " + " AND ".join(cds)

        with mkConn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, pms)
            return cursor.fetchone()[0]
    except Exception as e:
        lg.error(f"Error counting assets: {str(e)}")
        return 0


def getFiltered( usrId="", opts="all", search="", onlyFav=False, onlyArc=False, onlyLive=False, page=1, pageSize=24) -> list[models.Asset]:
    try:
        cds = []
        pms = []

        if usrId:
            cds.append("ownerId = ?")
            pms.append(usrId)

        if onlyFav:
            cds.append("isFavorite = 1")

        if onlyArc:
            cds.append("isArchived = 1")

        if onlyLive:
            cds.append("vdoId IS NOT NULL")

        if opts == "with_vectors":
            cds.append("isVectored = 1")
        elif opts == "without_vectors":
            cds.append("isVectored = 0")

        if search and len(search.strip()) > 0:
            cds.append("originalFileName LIKE ?")
            pms.append(f"%{search}%")

        query = "Select * From assets"
        if cds:
            query += " WHERE " + " AND ".join(cds)

        query += f" Order By autoId DESC"
        # query += f" ORDER BY {sort} {'DESC' if sortOrd == 'desc' else 'ASC'}"
        query += f" LIMIT {pageSize} OFFSET {(page - 1) * pageSize}"

        with mkConn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, pms)
            assets = []
            for row in cursor.fetchall():
                ass = models.Asset.fromDB(cursor, row)
                assets.append(ass)

            psql.exInfoFill(assets)
            return assets
    except Exception as e:
        lg.error(f"Error fetching assets: {str(e)}")
        return []


#========================================================================
# update
#========================================================================

def setVectoredBy(asset: models.Asset, done=1, cur: Optional[Cursor] = None):
    try:
        if cur:
            # Use provided cursor (for transactions)
            cur.execute("UPDATE assets SET isVectored=? WHERE id = ?", (done, asset.id))
        else:
            # Use context manager for standalone operation
            with mkConn() as conn:
                c = conn.cursor()
                c.execute("UPDATE assets SET isVectored=? WHERE id = ?", (done, asset.id))
                conn.commit()
    except Exception as e:
        raise mkErr(f"Failed to update vector status for asset[{asset.id}]", e)


def saveBy(asset: dict, c: Cursor) -> int:  #, onExist:Callable[[models.Asset],None]):
    try:
        assId = asset.get('id', None)
        if not assId: return 0

        exifInfo = asset.get('exifInfo', {})
        jsonExif = None
        if exifInfo:
            try:
                jsonExif = json.dumps(exifInfo, ensure_ascii=False, default=BaseDictModel.jsonSerializer)
                # lg.info(f"json: {jsonExif}")
            except Exception as e:
                raise mkErr("[pics.save] Error converting EXIF to JSON", e)

        c.execute("Select originalPath, pathThumbnail, pathPreview, pathVdo, jsonExif, isFavorite, isArchived From assets Where id = ?", (str(assId),))
        row = c.fetchone()

        if row is None:
            c.execute('''
                Insert Into assets (id, ownerId, deviceId, vdoId, type, originalFileName, originalPath,
                fileCreatedAt, fileModifiedAt, isFavorite, isArchived,
                localDateTime, pathThumbnail, pathPreview, pathVdo, jsonExif)
                Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(assId),
                str(asset.get('ownerId')),
                asset.get('deviceId'),
                str(asset.get('video_id')) if asset.get('video_id') else None,
                asset.get('type'),
                asset.get('originalFileName'),
                asset.get('originalPath'),
                asset.get('fileCreatedAt'),
                asset.get('fileModifiedAt'),
                asset.get('isFavorite'),
                1 if asset.get('visibility') == 'archive' else 0,

                asset.get('localDateTime'),
                asset.get('thumbnail_path'),
                asset.get('preview_path'),
                asset.get('video_path'),
                jsonExif,
            ))

            return 1  # new asset added

        # Check if update needed
        needUpdate = False
        if row['originalPath'] != asset.get('originalPath'): needUpdate = True
        if row['pathThumbnail'] != asset.get('thumbnail_path'): needUpdate = True
        if row['pathPreview'] != asset.get('preview_path'): needUpdate = True
        if row['pathVdo'] != (str(asset.get('video_path')) if asset.get('video_path') else None): needUpdate = True
        if row['jsonExif'] != jsonExif: needUpdate = True
        if row['isFavorite'] != asset.get('isFavorite'): needUpdate = True
        if row['isArchived'] != (1 if asset.get('visibility') == 'archive' else 0): needUpdate = True

        if needUpdate:
            c.execute('''
                Update assets Set
                    originalPath = ?,
                    pathThumbnail = ?,
                    pathPreview = ?,
                    pathVdo = ?,
                    jsonExif = ?,
                    isFavorite = ?,
                    isArchived = ?
                Where id = ?
            ''', (
                asset.get('originalPath'),
                asset.get('thumbnail_path'),
                asset.get('preview_path'),
                asset.get('video_path'),
                jsonExif,
                asset.get('isFavorite'),
                1 if asset.get('visibility') == 'archive' else 0,
                str(assId)
            ))
            return 2

        return 0
    except Exception as e:
        raise mkErr("Failed to save asset", e)


#========================================================================
# sim
#========================================================================

def getAnyNonSim(exclAids=[]) -> Optional[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            sql = "Select * From assets Where isVectored = 1 AND simOk!=1 AND json_array_length(simINfos) = 0"
            params = []

            if exclAids:
                qargs = ','.join(['?' for _ in exclAids])
                sql += f" AND autoId NOT IN ({qargs})"
                params.extend(exclAids)

            c.execute(sql, params)
            while True:
                row = c.fetchone()
                if row is None: return None
                asset = models.Asset.fromDB(c, row)

                import db
                if not db.dto.checkIsExclude(asset): return asset

    except Exception as e:
        raise mkErr("Failed to get non-sim asset", e)


def countSimOk(isOk=0):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM assets WHERE isVectored = 1 AND simOk = ?", (isOk,))
            count = c.fetchone()[0]
            # lg.info(f"[pics] count isOk[{isOk}] cnt[{count}]")
            return count
    except Exception as e:
        raise mkErr(f"Failed to count assets with simOk[{isOk}]", e)


def setSimGIDs(autoId: int, GID: int):
    try:
        with mkConn() as conn:
            c = conn.cursor()

            c.execute("SELECT simGIDs FROM assets WHERE autoId = ?", (autoId,))
            row = c.fetchone()
            if row:
                gids = json.loads(row[0]) if row[0] else []
                if GID not in gids:
                    gids.append(GID)
                    c.execute(
                        "UPDATE assets SET simGIDs = ? WHERE autoId = ?",
                        (json.dumps(gids), autoId)
                    )
                    conn.commit()
                    # lg.info(f"[pics] upd #{autoId} GID[{GID}] to simGIDs[{gids}]")
                    return True
            return False
    except Exception as e:
        raise mkErr(f"Failed to set simGIDs for asset[{autoId}]", e)



def setSimInfos(autoId: int, infos: List[models.SimInfo], isOk=0):
    if not infos or len(infos) <= 0:
        raise RuntimeError(f"Can't setSimInfos id[{autoId}] by [{type(infos)}], {tracebk.format_exc()}")

    try:
        with mkConn() as conn:
            c = conn.cursor()

            try:
                dictSimInfos = [sim.toDict() for sim in infos] if infos else []

                c.execute(
                    "UPDATE assets SET simOk = ?, simInfos = ? WHERE autoId = ?",
                    (isOk, json.dumps(dictSimInfos), autoId)
                )

                if not c.rowcount:
                    raise RuntimeError(f"update failed #{autoId}")

                conn.commit()
                # lg.info(f"[pics] upd #{autoId} simOK[{isOk}] simInfo[{len(infos)}]")

            except Exception as e:
                raise e
    except Exception as e:
        raise mkErr("Failed to set similar IDs", e)


def deleteBy(assets: List[models.Asset]):
    try:
        cntAll = len(assets)
        with mkConn() as conn:
            c = conn.cursor()

            # Get mainGIDs from assets to be deleted
            mainGIDs = [a.autoId for a in assets if a.vw.isMain]

            # 1. Delete incoming assets first
            assIds = [ass.id for ass in assets]
            if not assIds: raise RuntimeError(f"No asset IDs found")

            # 1.1 Delete from database
            qargs = ','.join(['?' for _ in assIds])
            c.execute(f"DELETE FROM assets WHERE id IN ({qargs})", assIds)
            count = c.rowcount

            if count != cntAll: raise mkErr(f"Failed to delete assets({cntAll}) with affected[{count}]")

            # 1.2 Delete from vector database using autoIds
            import db.vecs as vecs
            aids = [ass.autoId for ass in assets]
            vecs.deleteBy(aids)

            # 2. Handle other assets containing these mainGIDs
            if mainGIDs:
                # Find assets with any of these mainGIDs in simGIDs (where simOk=0)
                for mainGID in mainGIDs:
                    c.execute("""
                        SELECT id, simGIDs FROM assets
                        WHERE EXISTS (
                            SELECT 1 FROM json_each(simGIDs)
                            WHERE value = ?
                        ) AND simOk = 0
                    """, (mainGID,))

                    needUpdAssets = c.fetchall()

                    for assId, jsonGIDs in needUpdAssets:
                        if jsonGIDs:
                            gids = json.loads(jsonGIDs)
                            gids.remove(mainGID)
                            if gids:
                                c.execute(
                                    "UPDATE assets SET simGIDs = ? WHERE id = ?",
                                    (json.dumps(gids), assId)
                                )
                            else:  # If no GIDs left, clear the state
                                c.execute(
                                    "UPDATE assets SET simInfos = '[]', simGIDs = '[]' WHERE id = ?",
                                    (assId,)
                                )

            conn.commit()
            lg.info(f"[pics] delete by assIds[{cntAll}] rst[{count}] mainGIDs[{mainGIDs}]")

            return count
    except Exception as e:
        raise mkErr("Failed to delete assets", e)


def setResloveBy(assets: List[models.Asset]):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            autoIds = [ass.autoId for ass in assets]
            if not autoIds: return 0

            autoIds = list(set(autoIds))
            cnt = len(autoIds)

            qargs = ','.join(['?' for _ in autoIds])
            c.execute(f"UPDATE assets SET simOk = 1, simGIDs = '[]', simInfos = '[]' WHERE autoId IN ({qargs})", autoIds)
            count = c.rowcount
            if count != cnt: raise RuntimeError(f"effect[{count}] not match assets[{cnt}] ids[{qargs}]")
            conn.commit()
            lg.info(f"[pics] set simOk by autoIds[{len(autoIds)}] rst[{count}]")
            return count
    except Exception as e:
        raise mkErr("Failed to resolve sim assets", e)


# noinspection SqlWithoutWhere
def clearAllSimIds(keepSimOk=False):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            if keepSimOk:
                c.execute("UPDATE assets SET simInfos = '[]', simGIDs = '[]' WHERE simOk = 0")
                lg.info(f"Cleared similarity search results but kept resolved items")
            else:
                c.execute("UPDATE assets SET simOk = 0, simInfos = '[]', simGIDs = '[]'")
                lg.info(f"Cleared all similarity results")
            conn.commit()
            count = c.rowcount
            lg.info(f"Cleared similarity results for {count} assets")
            return count
    except Exception as e:
        raise mkErr("Failed to clear sim results", e)


def countHasSimIds(isOk=0):
    try:
        with mkConn() as conn:
            c = conn.cursor()
            sql = '''
                SELECT COUNT(*) FROM assets
                WHERE simOk = ? AND json_array_length(simInfos) > 0
            '''
            c.execute(sql, (isOk,))
            row = c.fetchone()
            count = row[0] if row else 0
            # lg.info(f"[pics] count have simInfos and type[{isOk}] cnt[{count}]")
            return count
    except Exception as e:
        raise mkErr(f"Failed to count assets with simInfos and simOk[{isOk}]", e)


# simOk mean that already resolve by user
def getAnySimPending() -> Optional[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM assets
                WHERE
                    simOk = 0 AND json_array_length(simInfos) > 1
                LIMIT 1
            """)
            row = c.fetchone()
            return models.Asset.fromDB(c, row) if row else None
    except Exception as e:
        raise mkErr("Failed to get pending assets", e)


def getAllSimOks(isOk=0) -> List[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM assets
                WHERE
                    simOk = ? AND json_array_length(simInfos) > 1
                ORDER BY autoId
            """, (isOk,))
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        raise mkErr("Failed to get all simOk assets", e)


# noinspection SqlWithoutWhere
def clearAllVectored():
    try:
        with mkConn() as cnn:
            c = cnn.cursor()
            c.execute("UPDATE assets SET isVectored=0")
            cnn.commit()
    except Exception as e:
        raise mkErr(f"Failed to set isVectored to 0", e)


# auto mark simOk=1 if simInfos only includes self
def setSimAutoMark():
    try:
        with mkConn() as cnn:
            c = cnn.cursor()
            c.execute("""
                UPDATE assets
                SET simOk = 1
                WHERE
                    simOk = 0 AND json_array_length(simInfos) = 1
                    AND EXISTS
                    (
                        SELECT 1 FROM json_each(simInfos) si
                            WHERE json_extract(si.value, '$.isSelf') = 1
                    )
            """)
            cnn.commit()
    except Exception as e:
        raise mkErr(f"Failed execute SimAutoMark", e)


def getAssetsByGID(gid: int) -> list[models.Asset]:
    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM assets
                WHERE EXISTS (
                    SELECT 1 FROM json_each(simGIDs)
                    WHERE value = ?
                ) AND json_array_length(simInfos) > 1
                ORDER BY json_array_length(simInfos) DESC, autoId
            """, (gid,))
            rows = c.fetchall()
            if not rows: return []
            assets = [models.Asset.fromDB(c, row) for row in rows]
            return assets
    except Exception as e:
        lg.error(f"Error fetching assets by GID: {str(e)}")
        return []


# if incGroup, include assets with same simGIDs, else only simInfos
# fetched rows will be set the asset.view props
def getSimAssets(autoId: int, incGroup=False) -> List[models.Asset]:
    import numpy as np
    from db import vecs

    # lg.info( f"[getSimAssets] loading #{autoId} inclGroup[ {incGroup} ]" )
    rst = []

    try:
        with mkConn() as conn:
            c = conn.cursor()
            c.execute("""
                WITH main_check AS (
                    SELECT DISTINCT gid.value as main_autoId
                    FROM assets a2
                    CROSS JOIN json_each(a2.simGIDs) gid
                    WHERE a2.autoId != gid.value
                )
                SELECT
                    a.*,
                    CASE WHEN mc.main_autoId IS NOT NULL THEN 1 ELSE 0 END as isMain
                FROM assets a
                LEFT JOIN main_check mc ON a.autoId = mc.main_autoId
                WHERE a.autoId = ?
            """, (autoId,))
            row = c.fetchone()
            if row is None:
                raise RuntimeError(f"[pics] SimGroup Root asset #{autoId} not found")

            root = models.Asset.fromDB(c, row)
            root.vw.isMain = bool(row['isMain'])
            rst = [root]

            if not incGroup:
                if not root.simInfos or len(root.simInfos) <= 1: return rst

                simAids = [info.aid for info in root.simInfos if not info.isSelf]
                if not simAids: return [root]

                qargs = ','.join(['?' for _ in simAids])
                c.execute(f"""
                    WITH main_check AS (
                        SELECT DISTINCT gid.value as main_autoId
                        FROM assets a2
                        CROSS JOIN json_each(a2.simGIDs) gid
                        WHERE a2.autoId != gid.value
                    )
                    SELECT
                        a.*,
                        CASE WHEN mc.main_autoId IS NOT NULL THEN 1 ELSE 0 END as isMain
                    FROM assets a
                    LEFT JOIN main_check mc ON a.autoId = mc.main_autoId
                    WHERE a.autoId IN ({qargs})
                """, simAids)

                rows = c.fetchall()


                assets = []
                for row in rows:
                    ass = models.Asset.fromDB(c, row)
                    ass.vw.isMain = bool(row['isMain'])
                    ass.vw.score = next((info.score for info in root.simInfos if info.aid == ass.autoId), 0)
                    assets.append(ass)

                assetMap = {asset.autoId: asset for asset in assets}

                sortAss = []
                for simInfo in sorted(root.simInfos, key=lambda x: x.score or 0, reverse=True):
                    if simInfo.aid in assetMap:
                        sortAss.append(assetMap[simInfo.aid])

                rst.extend(sortAss)
            else:
                if not root.simGIDs: return rst

                # Find all assets in the group (bidirectional query)
                # 1. Assets sharing any GID with root
                # 2. Assets with root.autoId in their simGIDs
                gid_placeholders = ','.join(['?' for _ in root.simGIDs])
                c.execute(f"""
                    WITH main_check AS (
                        SELECT DISTINCT gid.value as main_autoId
                        FROM assets a2
                        CROSS JOIN json_each(a2.simGIDs) gid
                        WHERE a2.autoId != gid.value
                    )
                    SELECT
                        a.*,
                        CASE WHEN mc.main_autoId IS NOT NULL THEN 1 ELSE 0 END as isMain
                    FROM assets a
                    LEFT JOIN main_check mc ON a.autoId = mc.main_autoId
                    WHERE a.autoId != ? AND (
                        EXISTS (
                            SELECT 1 FROM json_each(a.simGIDs)
                            WHERE value IN ({gid_placeholders})
                        )
                        OR EXISTS (
                            SELECT 1 FROM json_each(a.simGIDs)
                            WHERE value = ?
                        )
                    )
                """, [autoId] + root.simGIDs + [root.autoId])
                rows = c.fetchall()

                if not rows: return rst

                assets = []
                for row in rows:
                    ass = models.Asset.fromDB(c, row)
                    ass.vw.isMain = bool(row['isMain'])
                    assets.append(ass)

                try:
                    rootVec = vecs.getBy(root.autoId)
                    rootVecNp = np.array(rootVec)

                    # Get autoIds from root's simInfos
                    rootSimAids = {info.aid for info in root.simInfos}

                    # Batch get all vectors at once to avoid N+1 queries
                    assetIds = [ass.autoId for ass in assets]
                    assVecs = vecs.getAllBy(assetIds)

                    assScores = []
                    for ass in assets:
                        if ass.autoId not in assVecs:
                            lg.warn(f"[pics] Vector not found for asset {ass.autoId}")
                            continue

                        assVecNp = np.array(assVecs[ass.autoId])
                        score = np.dot(rootVecNp, assVecNp)

                        # Only set isRelats for assets NOT in root's simInfos
                        ass.vw.isRelats = ass.autoId not in rootSimAids
                        ass.vw.score = score

                        assScores.append((ass, score))

                    assScores.sort(key=lambda x: x[1], reverse=True)
                    rst.extend([ass for ass, _ in assScores])

                except Exception as e:
                    lg.error(f"[pics] Error processing vectors: {str(e)}")
                    rst.extend(assets)




            # lg.info( f"[getSimAssets] fetched[ {len(rst)} ] inclGroup[ {incGroup} ]" )
            psql.exInfoFill(rst)
            return rst
    except Exception as e:
        raise mkErr(f"Failed to get similar group for root #{autoId}", e)


def countSimPending():
    try:
        with mkConn() as conn:
            c = conn.cursor()
            # Count all leader assets referenced in simGIDs
            c.execute("""
                WITH allGIDs AS (
                    SELECT DISTINCT gid.value as gid
                    FROM assets a
                    CROSS JOIN json_each(a.simGIDs) gid
                    WHERE a.simOk = 0 AND json_array_length(a.simInfos) > 1
                )
                SELECT COUNT(*) FROM assets a
                INNER JOIN allGIDs g ON a.autoId = g.gid
                WHERE a.simOk = 0 AND json_array_length(a.simInfos) > 1
            """)
            cnt = c.fetchone()[0]
            return cnt
    except Exception as e:
        raise mkErr(f"Failed to count assets pending", e)


def getPagedPending(page=1, size=20) -> list[models.Asset]:
    try:
        with mkConn() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * size

            # Get all leader assets referenced in simGIDs
            cursor.execute("""
                WITH allGIDs AS (
                    SELECT DISTINCT gid.value as gid
                    FROM assets a
                    CROSS JOIN json_each(a.simGIDs) gid
                    WHERE a.simOk = 0 AND json_array_length(a.simInfos) > 1
                ),
                gidCounts AS (
                    SELECT
                        gid.value as gid,
                        COUNT(*) as cntRelats
                    FROM assets a
                    CROSS JOIN json_each(a.simGIDs) gid
                    WHERE a.simOk = 0 AND json_array_length(a.simInfos) > 1
                      AND a.autoId != gid.value
                    GROUP BY gid.value
                )
                SELECT
                    a.*,
                    COALESCE(gc.cntRelats, 0) as cntRelats
                FROM assets a
                INNER JOIN allGIDs g ON a.autoId = g.gid
                LEFT JOIN gidCounts gc ON a.autoId = gc.gid
                WHERE a.simOk = 0 AND json_array_length(a.simInfos) > 1
                ORDER BY json_array_length(a.simInfos) DESC, a.autoId
                LIMIT ? OFFSET ?
            """, (size, offset))

            leaders = []
            for row in cursor.fetchall():
                asset = models.Asset.fromDB(cursor, row)
                asset.vw.cntRelats = row['cntRelats']
                leaders.append(asset)

            return leaders
    except Exception as e:
        lg.error(f"Error fetching assets: {str(e)}")
        return []
