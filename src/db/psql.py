import os
import time
from typing import Optional, List, Dict
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

import imgs
from conf import ks, envs
from util import log
from mod import models
from util.err import mkErr

lg = log.get(__name__)


def init():
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        register_heif_opener = None
        lg.info("pillow-heif not available, skipping HEIC/HEIF support")

    host = envs.psqlHost
    port = envs.psqlPort
    db = envs.psqlDb
    uid = envs.psqlUser

    if not all([host, port, db, uid]): raise RuntimeError("PostgreSQL connection settings not initialized.")

    try:
        with mkConn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception as e:
        lg.error(f"PostgreSQL connection test failed: {str(e)}")
        return False


@contextmanager
def mkConn():
    host = envs.psqlHost
    port = envs.psqlPort
    db = envs.psqlDb
    uid = envs.psqlUser
    pw = envs.psqlPass

    conn = None
    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=db,
            user=uid,
            password=pw
        )
        yield conn
    except Exception: raise
    finally:
        if conn: conn.close()


def chk():
    try:
        with mkConn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT 1")
        return True
    except Exception as e:
        raise mkErr(f"Failed to connect to PostgreSQL", e)


def fetchUser(usrId: str) -> Optional[models.Usr]:
    try:
        with mkConn() as conn:
            sql = """
            Select
                u.id,
                u.name,
                u.email
            From users u
            Where u.id = %s
            """
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (usrId,))
                row = cursor.fetchone()

                if not row: raise RuntimeError( "no db row" )

                return models.Usr.fromDic(row)

    except Exception as e:
        raise mkErr(f"Failed to fetch userId[{usrId}]", e)

def fetchUsers() -> List[models.Usr]:
    try:
        with mkConn() as conn:
            sql = """
            Select id, name, email From users
            """
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql)
                dics = cursor.fetchall()
                usrs = [models.Usr.fromDic(d) for d in dics]

                nams = []
                for u in usrs: nams.append(u.name)

                lg.info(f"[psql] fetch users[{len(usrs)}] {nams}")

                return usrs
    except Exception as e:
        raise mkErr(f"Failed to fetch users", e)


def count(usrId=None, assetType="IMAGE"):
    try:
        with mkConn() as conn:
            with conn.cursor() as cursor:
                #lg.info( f"[psql] count userId[{usrId}]" )

                # noinspection SqlConstantExpression
                sql = "Select Count(*) From assets Where 1=1"
                params = []

                if assetType:
                    sql += " AND type = %s"
                    params.append(assetType)

                if usrId:
                    sql += ' AND "ownerId" = %s'
                    params.append(usrId)

                sql += " AND status = 'active'"

                cursor.execute(sql, params)
                rst = cursor.fetchone()
                count = rst[0] if rst else 0

                #lg.info( f"[psql] count userId[{usrId}] rst[{count}]" )

                return count
    except Exception as e:
        raise mkErr(f"Failed to count assets", e)




def testAssetsPath():
    try:
        with mkConn() as conn:
            sql = "Select path From asset_files Limit 5"
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

                isOk = False

                # lg.info( f"[psql] test AccessPath.. fetched: {len(rows)}" )

                if not rows or not len(rows): return "No Assets"

                for row in rows:
                    pathDB = row.get("path", "")
                    if pathDB:
                        original_path = pathDB
                        pathFi = envs.pth.full(pathDB)
                        isOk = os.path.exists(pathFi)
                        # lg.info( f"[psql] test isOk[{isOk}] path: {path}" )
                        if isOk: return [ "OK" ]
                        else:
                            return [
                                "Asset file not found at expected path:",
                                f"  {pathFi}",
                                "",
                                f"This path was constructed from:",
                                f"  IMMICH_PATH + DB Path",
                                f"  DB Path: '{original_path}'",
                                "",
                                "Please verify IMMICH_PATH environment variable matches your Immich installation path."
                            ]

                return [
                    "Asset path test failed.",
                    "Unable to find any accessible asset files.",
                ]

    except Exception as e:
        raise mkErr("Failed to test assets path. Please verify IMMICH_PATH environment variable matches your Immich installation path", e)



def fetchAssets(usr: models.Usr, onUpdate: models.IFnProg):
    usrId = usr.id
    asType = "IMAGE"

    try:
        chk()

        onUpdate(11, f"start querying {usrId}")

        with mkConn() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                # count all
                cntSql = "Select Count( * ) From assets Where status = 'active' And type = %s"
                cntArs = [asType]

                if usrId:
                    cntSql += " AND \"ownerId\" = %s"
                    cntArs.append(usrId)

                cursor.execute(cntSql, cntArs)
                rst = cursor.fetchone()
                if not rst: raise RuntimeError( "cannot count assets" )

                cntAll = rst.get("count", 0)

                if not cntAll: raise RuntimeError(f"fetch target type[{asType}] not found")

                # lg.info(f"Found {cntAll} {asType.lower()} assets...")
                onUpdate(15, f"start querying {cntAll}")

                #----------------------------------------------------------------
                # query assets
                #----------------------------------------------------------------
                sql = "Select * From assets Where status = 'active' And type = %s"

                params = [asType]

                if usrId:
                    sql += " AND \"ownerId\" = %s"
                    params.append(usrId)

                sql += " ORDER BY \"createdAt\" DESC"

                cursor.execute(sql, params)

                szBatch = 100
                szChunk = 100
                assets = []
                cntFetched = 0

                tStart = time.time()

                while True:
                    batch = cursor.fetchmany(szBatch)
                    if not batch: break

                    cntFetched += len(batch)

                    for row in batch: assets.append(row)

                    # if cntAll > 0:
                    #     if cntFetched > 0:
                    #         tmUsed = time.time() - tStart
                    #         tPerItem = tmUsed / cntFetched
                    #         remCnt = cntAll - cntFetched
                    #         remTime = tPerItem * remCnt
                    #         remMins = int(remTime / 60)
                    #         tmSuffix = f"remain: {remMins} mins"
                    #     else:
                    #         tmSuffix = "calcuating..."

                        # report("fetch", cntFetched, cntAll, f"processed {cntFetched}/{cntAll} ... {tmSuffix}")

                onUpdate(30, "main assets done... query for files..")

                #----------------------------------------------------------------
                # query asset files
                #----------------------------------------------------------------
                flsSql = """
                   Select "assetId", type, path
                   From asset_files
                   Where "assetId" = ANY(%s)
                """

                assetIds = [a['id'] for a in assets]
                afs = []

                for idx, i in enumerate(range(0, len(assetIds), szChunk)):
                    chunk = assetIds[i:i + szChunk]
                    cursor.execute(flsSql, (chunk,))
                    chunkRows = cursor.fetchall()
                    afs.extend(chunkRows)

                    chunkPct = min((idx + 1) * szChunk, len(assetIds))

                onUpdate(40, "files ready, combine data...")

                dictFiles = {}
                for af in afs:
                    assetId = af['assetId']
                    typ = af['type']
                    path = af['path']
                    if assetId not in dictFiles: dictFiles[assetId] = {}
                    dictFiles[assetId][typ] = path

                #----------------------------------------------------------------
                # query exif
                #----------------------------------------------------------------
                exifSql = """
                    Select *
                    From exif
                    Where "assetId" = ANY(%s)
                """

                exifData = {}
                for idx, i in enumerate(range(0, len(assetIds), szChunk)):
                    chunk = assetIds[i:i + szChunk]

                    cursor.execute(exifSql, (chunk,))
                    chunkRows = cursor.fetchall()

                    for row in chunkRows:
                        assetId = row['assetId']
                        exifItem = {}

                        for key, val in row.items():
                            if key == 'assetId': continue

                            if key in ('dateTimeOriginal', 'modifyDate') and val is not None:
                                if isinstance(val, str):
                                    exifItem[key] = val
                                else:
                                    exifItem[key] = val.isoformat() if val else None
                            elif val is not None:
                                exifItem[key] = val

                        if exifItem: exifData[assetId] = exifItem

                    chunkPct = min((idx + 1) * szChunk, len(assetIds))

                #----------------------------------------------------------------
                # query livephoto videos
                #----------------------------------------------------------------
                onUpdate(42, "query livephoto videos...")

                livePhotoSql = """
                    -- Method 1: Direct livePhotoVideoId
                    SELECT
                        a.id AS photo_id,
                        a."livePhotoVideoId" AS video_id,
                        v."encodedVideoPath" AS video_path,
                        v."originalPath" AS video_original_path
                    FROM assets a
                    JOIN assets v ON v.id = a."livePhotoVideoId" AND v.type = 'VIDEO'
                    WHERE a."livePhotoVideoId" IS NOT NULL
                    AND a.type = 'IMAGE'
                    AND a.id = ANY(%s)

                    UNION

                    -- Method 2: Match by livePhotoCID (for photos without livePhotoVideoId)
                    SELECT DISTINCT
                        a.id AS photo_id,
                        v.id AS video_id,
                        v."encodedVideoPath" AS video_path,
                        v."originalPath" AS video_original_path
                    FROM assets a
                    JOIN exif ae ON a.id = ae."assetId"
                    JOIN exif ve ON ae."livePhotoCID" = ve."livePhotoCID"
                    JOIN assets v ON ve."assetId" = v.id
                    WHERE ae."livePhotoCID" IS NOT NULL
                    AND a."livePhotoVideoId" IS NULL
                    AND a.type = 'IMAGE'
                    AND v.type = 'VIDEO'
                    AND v.id != a.id
                    AND a.id = ANY(%s)
                """

                livePaths = {}
                liveVdoIds = {}
                for idx, i in enumerate(range(0, len(assetIds), szChunk)):
                    chunk = assetIds[i:i + szChunk]
                    cursor.execute(livePhotoSql, (chunk, chunk))
                    chunkRows = cursor.fetchall()

                    for row in chunkRows:
                        photoId = row['photo_id']
                        videoId = row['video_id']
                        videoPath = row['video_path']
                        originalVideoPath = row['video_original_path']

                        finalPath = videoPath if videoPath else originalVideoPath
                        if finalPath:
                            livePaths[photoId] = envs.pth.normalize(finalPath)
                            liveVdoIds[photoId] = videoId

                #----------------------------------------------------------------
                # combine & fetch thumbnail image
                #----------------------------------------------------------------
                onUpdate(45, "files ready, combine data...")

                cntOk = 0
                cntErr = 0

                rst = []

                for asset in assets:
                    assetId = asset['id']
                    if assetId in dictFiles:
                        for typ, path in dictFiles[assetId].items():
                            if typ == ks.db.thumbnail: asset['thumbnail_path'] = envs.pth.normalize(path)
                            elif typ == ks.db.preview: asset['preview_path'] = envs.pth.normalize(path)

                    if assetId in livePaths: asset['video_path'] = livePaths[assetId]
                    if assetId in liveVdoIds: asset['video_id'] = liveVdoIds[assetId]

                    if assetId in exifData:
                        asset['exifInfo'] = exifData[assetId]
                    else:
                        lg.warn(f"[exif] NotFound.. assetId[{assetId}]")

                    # final check
                    pathThumbnail = asset.get('thumbnail_path')
                    if not pathThumbnail:
                        cntErr += 1
                        lg.warn(f"[psql] ignore non thumbnail asset: {str(asset.get('id'))}")
                        continue

                    cntOk += 1
                    rst.append(asset)

                    # if len(assets) > 0 and (cntOk % 100 == 0 or cntOk == len(assets)):
                    #     report("combine", cntOk, len(assets), f"processing {cntOk}/{len(assets)}...")

                lg.info(f"Successfully fetched {len(rst)} {asType.lower()} assets")
                onUpdate(5, f"Successfully fetched {len(rst)} {asType.lower()} assets")

                return rst
    except Exception as e:
        msg = f"Failed to FetchAssets: {str(e)}"
        raise mkErr(msg, e)


#------------------------------------------------------
# Albums Operations
#------------------------------------------------------
def getUsrAlbumsBy(usrId: str) -> List[models.Album]:
    try:
        with mkConn() as conn:
            sql = """
            Select
                a.id,
                a."ownerId",
                a."albumName",
                a.description,
                a."createdAt",
                a."updatedAt",
                a."albumThumbnailAssetId",
                a."isActivityEnabled",
                a."order"
            From albums a
            Where a."ownerId" = %s And a."deletedAt" Is Null
            Order By a."createdAt" Desc
            """
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (usrId,))
                rows = cursor.fetchall()
                return [models.Album.fromDic(row) for row in rows]
    except Exception as e:
        raise mkErr(f"Failed to fetch albums for userId[{usrId}]", e)


def getAlbumAssetIds(albumId: str) -> List[str]:
    try:
        with mkConn() as conn:
            sql = """
            Select aa."assetsId"
            From albums_assets_assets aa
            Join albums a On a.id = aa."albumsId"
            Where aa."albumsId" = %s And a."deletedAt" Is Null
            Order By aa."createdAt" Desc
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (albumId,))
                rows = cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        raise mkErr(f"Failed to fetch assets for albumId[{albumId}]", e)


def getAssetAlbums(assetId: str) -> List[models.Album]:
    try:
        with mkConn() as conn:
            sql = """
            Select
                a.id,
                a."ownerId",
                a."albumName",
                a.description,
                a."createdAt",
                a."updatedAt",
                a."albumThumbnailAssetId",
                a."isActivityEnabled",
                a."order"
            From albums a
            Join albums_assets_assets aa On a.id = aa."albumsId"
            Where aa."assetsId" = %s And a."deletedAt" Is Null
            Order By a."createdAt" Desc
            """
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (assetId,))
                rows = cursor.fetchall()
                return [models.Album.fromDic(row) for row in rows]
    except Exception as e:
        raise mkErr(f"Failed to fetch albums for assetId[{assetId}]", e)


def addToAlbum(albumId: str, assetIds: List[str]) -> int:
    if not assetIds: return 0

    try:
        with mkConn() as conn:
            with conn.cursor() as cursor:
                checkSql = "Select 1 From albums Where id = %s And \"deletedAt\" Is Null"
                cursor.execute(checkSql, (albumId,))
                if not cursor.fetchone(): raise RuntimeError(f"Album not found: {albumId}")

                existingSql = """
                Select "assetsId" From albums_assets_assets Where "albumsId" = %s And "assetsId" = ANY(%s)
                """
                cursor.execute(existingSql, (albumId, assetIds))
                existing = {row[0] for row in cursor.fetchall()}

                newAssetIds = [aid for aid in assetIds if aid not in existing]
                if not newAssetIds: return 0

                values = [(albumId, aid) for aid in newAssetIds]
                insertSql = """
                Insert Into albums_assets_assets ("albumsId", "assetsId", "createdAt")
                Values (%s, %s, Now())
                """
                cursor.executemany(insertSql, values)
                conn.commit()

                return len(newAssetIds)
    except Exception as e:
        raise mkErr(f"Failed to add assets to album[{albumId}]", e)


def delFromAlbumBy(albumId: str, assetIds: List[str]) -> int:
    if not assetIds: return 0

    try:
        with mkConn() as conn:
            sql = """
            Delete From albums_assets_assets
            Where "albumsId" = %s And "assetsId" = ANY(%s)
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (albumId, assetIds))
                removedCnt = cursor.rowcount
                conn.commit()
                return removedCnt
    except Exception as e:
        raise mkErr(f"Failed to remove assets from album[{albumId}]", e)


#------------------------------------------------------
# Favorites Operations
#------------------------------------------------------
def getFavoriteIds(usrId: str) -> List[str]:
    try:
        with mkConn() as conn:
            sql = """
            Select id From assets
            Where "ownerId" = %s And "isFavorite" = true And status = 'active'
            Order By "updatedAt" Desc
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (usrId,))
                rows = cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        raise mkErr(f"Failed to fetch favorite assets for userId[{usrId}]", e)


def isFavorite(assetId: str) -> bool:
    try:
        with mkConn() as conn:
            sql = "Select \"isFavorite\" From assets Where id = %s"
            with conn.cursor() as cursor:
                cursor.execute(sql, (assetId,))
                row = cursor.fetchone()
                return row[0] if row else False
    except Exception as e:
        raise mkErr(f"Failed to check favorite status for assetId[{assetId}]", e)


def updFavoriteBy(assetIds: List[str], isFav: bool) -> int:
    if not assetIds: return 0

    try:
        with mkConn() as conn:
            sql = """
            Update assets Set "isFavorite" = %s, "updatedAt" = Now()
            Where id = ANY(%s) And status = 'active'
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (isFav, assetIds))
                updatedCnt = cursor.rowcount
                conn.commit()
                return updatedCnt
    except Exception as e:
        raise mkErr(f"Failed to update favorite status for assets", e)


#------------------------------------------------------
# Archive Operations
#------------------------------------------------------
def getArchivedIds(usrId: str) -> List[str]:
    try:
        with mkConn() as conn:
            sql = """
            Select id From assets
            Where "ownerId" = %s And visibility = 'archive' And status = 'active'
            Order By "updatedAt" Desc
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (usrId,))
                rows = cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        raise mkErr(f"Failed to fetch archived assets for userId[{usrId}]", e)


def isArchived(assetId: str) -> bool:
    try:
        with mkConn() as conn:
            sql = "Select visibility From assets Where id = %s"
            with conn.cursor() as cursor:
                cursor.execute(sql, (assetId,))
                row = cursor.fetchone()
                return row[0] == 'archive' if row else False
    except Exception as e:
        raise mkErr(f"Failed to check archive status for assetId[{assetId}]", e)


def updArchiveBy(assetIds: List[str], isArchived: bool) -> int:
    if not assetIds: return 0

    try:
        with mkConn() as conn:
            visibility = 'archive' if isArchived else 'timeline'
            sql = """
            Update assets Set visibility = %s, "updatedAt" = Now()
            Where id = ANY(%s) And status = 'active'
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (visibility, assetIds))
                updatedCnt = cursor.rowcount
                conn.commit()
                return updatedCnt
    except Exception as e:
        raise mkErr(f"Failed to update archive status for assets", e)


#------------------------------------------------------
# Extended Info Operations
#------------------------------------------------------
def fetchExInfo(assetId: str) -> Optional[models.AssetExInfo]:
    rst = fetchExInfos([assetId])
    return rst.get(assetId)


def fetchExInfos(assetIds: List[str]) -> Dict[str, models.AssetExInfo]:
    if not assetIds: return {}

    try:
        with mkConn() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rst = {}
                szChunk = 100

                for assetId in assetIds: rst[str(assetId).strip()] = models.AssetExInfo()

                # Fetch albums in chunks
                for i in range(0, len(assetIds), szChunk):
                    chunk = assetIds[i:i + szChunk]
                    albSql = """
                    Select aaa."assetsId", a.id, a."ownerId", a."albumName", a.description,
                           a."createdAt", a."updatedAt", a."albumThumbnailAssetId", a."isActivityEnabled", a."order"
                    From albums a
                    Join albums_assets_assets aaa On a.id = aaa."albumsId"
                    Where aaa."assetsId" = ANY(%s) And a."deletedAt" Is Null
                    Order By a."createdAt" Desc
                    """
                    cursor.execute(albSql, (chunk,))
                    albRows = cursor.fetchall()
                    lg.info(f"Album query returned {len(albRows)} rows for chunk {chunk}")

                    for row in albRows:
                        assetId = str(row['assetsId']).strip()
                        if assetId in rst:
                            albData = {k: v for k, v in row.items() if k != 'assetsId'}
                            rst[assetId].albs.append(models.Album.fromDic(albData))

                # Fetch faces in chunks
                for i in range(0, len(assetIds), szChunk):
                    chunk = assetIds[i:i + szChunk]
                    facSql = """
                    Select af."assetId", af.id, af."personId", p.name, p."ownerId",
                           af."imageWidth", af."imageHeight", af."boundingBoxX1", af."boundingBoxY1",
                           af."boundingBoxX2", af."boundingBoxY2", af."sourceType"
                    From asset_faces af
                    Join person p On af."personId" = p.id
                    Where af."assetId" = ANY(%s) And af."deletedAt" Is Null
                    """
                    cursor.execute(facSql, (chunk,))
                    facRows = cursor.fetchall()

                    for row in facRows:
                        assetId = str(row['assetId']).strip()
                        if assetId in rst:
                            facData = {k: v for k, v in row.items() if k != 'assetId'}
                            rst[assetId].facs.append(models.AssetFace.fromDic(facData))

                # Fetch tags in chunks
                for i in range(0, len(assetIds), szChunk):
                    chunk = assetIds[i:i + szChunk]
                    tagSql = """
                    Select ta."assetsId", t.id, t.value, t."userId"
                    From tags t
                    Join tag_asset ta On t.id = ta."tagsId"
                    Where ta."assetsId" = ANY(%s)
                    """
                    cursor.execute(tagSql, (chunk,))
                    tagRows = cursor.fetchall()

                    for row in tagRows:
                        assetId = str(row['assetsId']).strip()
                        if assetId in rst:
                            tagData = {k: v for k, v in row.items() if k != 'assetsId'}
                            rst[assetId].tags.append(models.Tags.fromDic(tagData))

                return rst

    except Exception as e:
        raise mkErr(f"Failed to fetch extended info for assetIds[{len(assetIds)}]", e)


def exInfoFill(rst: List[models.Asset]):
    if not rst: return

    assetIds = [str(asset.id) for asset in rst]
    exInfos = fetchExInfos(assetIds)

    for asset in rst:
        assetId = str(asset.id)
        asset.ex = exInfos.get(assetId)


