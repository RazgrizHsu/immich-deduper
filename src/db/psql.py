import os
import time
from typing import Optional, List, Dict, cast, LiteralString
from contextlib import contextmanager
from datetime import datetime, timezone
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row


def Q(s: str) -> LiteralString: return cast(LiteralString, s)

from conf import ks, envs
import rtm
from util import log
from mod import models
from util.err import mkErr

lg = log.get(__name__)


@dataclass
class SchemaInfo:
	# Main table names (singular vs plural)
	asset: str = 'asset'
	album: str = 'album'
	tag: str = 'tag'
	user: str = 'user'
	# Related table names (old: exif/asset_files/asset_faces, new: asset_exif/asset_file/asset_face)
	assetExif: str = 'asset_exif'
	assetFile: str = 'asset_file'
	assetFace: str = 'asset_face'
	# Junction table names
	albumAsset: str = 'album_asset'
	tagAsset: str = 'tag_asset'
	albumUser: str = 'album_user'
	# Junction table column names
	albumAssetAlbumId: str = 'albumId'
	albumAssetAssetId: str = 'assetId'
	tagAssetTagId: str = 'tagId'
	tagAssetAssetId: str = 'assetId'
	albumUserAlbumId: str = 'albumId'
	albumUserUserId: str = 'userId'

_schema = None

def detectSchema():
	"""
	Detect Immich database schema to support different versions.
	Called once during init() and cached globally.

	Detects:
	- Table names (plural vs singular: assets/asset, albums/album, etc.)
	- Junction table column names (plural vs singular: albumsId/albumId, assetsId/assetId, etc.)
	"""
	global _schema

	if _schema is not None: return _schema

	schema = SchemaInfo()

	try:
		with mkConn() as conn:
			with conn.cursor() as c:
				# Detect main table names (plural vs singular)
				c.execute("""
					SELECT table_name FROM information_schema.tables
					WHERE table_schema = 'public'
					AND table_name IN ('assets', 'asset', 'albums', 'album', 'tags', 'tag', 'users', 'user')
					ORDER BY table_name
				""")
				tables = {row[0] for row in c.fetchall()}

				schema.asset = 'asset' if 'asset' in tables else 'assets'
				schema.album = 'album' if 'album' in tables else 'albums'
				schema.tag = 'tag' if 'tag' in tables else 'tags'
				schema.user = 'user' if 'user' in tables else 'users'

				# Detect related table names (old: exif/asset_files/asset_faces, new: asset_exif/asset_file/asset_face)
				c.execute("""
					SELECT table_name FROM information_schema.tables
					WHERE table_schema = 'public'
					AND table_name IN ('asset_exif', 'exif', 'asset_file', 'asset_files', 'asset_face', 'asset_faces')
				""")
				relTables = {row[0] for row in c.fetchall()}
				schema.assetExif = 'asset_exif' if 'asset_exif' in relTables else 'exif'
				schema.assetFile = 'asset_file' if 'asset_file' in relTables else 'asset_files'
				schema.assetFace = 'asset_face' if 'asset_face' in relTables else 'asset_faces'

				# Detect junction table names (new: album_asset, old: albums_assets_assets)
				c.execute("""
					SELECT table_name FROM information_schema.tables
					WHERE table_schema = 'public'
					AND table_name IN ('album_asset', 'albums_assets_assets',
										'tag_asset', 'tags_assets_assets',
										'album_user', 'albums_shared_users_users')
				""")
				jTables = {row[0] for row in c.fetchall()}
				schema.albumAsset = 'album_asset' if 'album_asset' in jTables else 'albums_assets_assets'
				schema.tagAsset = 'tag_asset' if 'tag_asset' in jTables else 'tags_assets_assets'
				schema.albumUser = 'album_user' if 'album_user' in jTables else 'albums_shared_users_users'

				# Detect album_asset junction table column names
				c.execute(Q(f"""
					SELECT column_name FROM information_schema.columns
					WHERE table_schema = 'public'
					AND table_name = '{schema.albumAsset}'
					AND (column_name LIKE '%albumId' OR column_name LIKE '%albumsId'
							OR column_name LIKE '%assetId' OR column_name LIKE '%assetsId')
				"""))
				cols = {row[0] for row in c.fetchall()}
				schema.albumAssetAlbumId = 'albumId' if 'albumId' in cols else 'albumsId'
				schema.albumAssetAssetId = 'assetId' if 'assetId' in cols else 'assetsId'

				# Detect tag_asset junction table column names
				c.execute(Q(f"""
					SELECT column_name FROM information_schema.columns
					WHERE table_schema = 'public'
					AND table_name = '{schema.tagAsset}'
					AND (column_name LIKE '%tagId' OR column_name LIKE '%tagsId'
							OR column_name LIKE '%assetId' OR column_name LIKE '%assetsId')
				"""))
				cols = {row[0] for row in c.fetchall()}
				schema.tagAssetTagId = 'tagId' if 'tagId' in cols else 'tagsId'
				schema.tagAssetAssetId = 'assetId' if 'assetId' in cols else 'assetsId'

				# Detect album_user junction table column names
				c.execute(Q(f"""
					SELECT column_name FROM information_schema.columns
					WHERE table_schema = 'public'
					AND table_name = '{schema.albumUser}'
					AND (column_name LIKE '%albumId' OR column_name LIKE '%albumsId'
							OR column_name LIKE '%userId' OR column_name LIKE '%usersId')
				"""))
				cols = {row[0] for row in c.fetchall()}
				schema.albumUserAlbumId = 'albumId' if 'albumId' in cols else 'albumsId'
				schema.albumUserUserId = 'userId' if 'userId' in cols else 'usersId'

				lg.info(f"Schema detected - Tables: asset={schema.asset}, album={schema.album}, tag={schema.tag}, user={schema.user}")
				lg.info(f"Schema detected - Junction: albumAsset={schema.albumAsset}, tagAsset={schema.tagAsset}, albumUser={schema.albumUser}")
				lg.info(f"Schema detected - albumAsset cols: albumId={schema.albumAssetAlbumId}, assetId={schema.albumAssetAssetId}")
				lg.info(f"Schema detected - tagAsset cols: tagId={schema.tagAssetTagId}, assetId={schema.tagAssetAssetId}")

				_schema = schema
				return schema
	except Exception as e: raise mkErr("Failed to detect database schema", e)


def getSchema():
	global _schema
	if _schema is None: raise RuntimeError("Schema not detected yet. Call init() first.")
	return _schema


def setup_safe_timestamp_loader():
	"""Setup custom timestamp loader to handle BC dates and out-of-range timestamps"""
	try:
		from psycopg.types.datetime import TimestamptzLoader, TimestampLoader
		import psycopg

		class SafeTimestamptzLoader(TimestamptzLoader):
			def load(self, data):
				try: return super().load(data)
				except (ValueError, OverflowError, psycopg.DataError) as e:
					if "year" in str(e) and ("out of range" in str(e) or "before year 1" in str(e)):
						try: data_str = bytes(data).decode('utf-8')
						except (UnicodeDecodeError, TypeError): data_str = repr(data)[:50]  # Limit length
						lg.warning(f"Replaced invalid timestamptz with default: {data_str} - {e}")
						# Return year 2000 as marker for problematic data
						return datetime(2000, 1, 1, tzinfo=timezone.utc)
					raise

		class SafeTimestampLoader(TimestampLoader):
			def load(self, data):
				try: return super().load(data)
				except (ValueError, OverflowError, psycopg.DataError) as e:
					if "year" in str(e) and ("out of range" in str(e) or "before year 1" in str(e)):
						try: data_str = bytes(data).decode('utf-8')
						except (UnicodeDecodeError, TypeError): data_str = repr(data)[:50]  # Limit length
						lg.warning(f"Replaced invalid timestamp with default: {data_str} - {e}")
						# Return year 2000 as marker for problematic data
						return datetime(2000, 1, 1)
					raise

		# Register globally using official psycopg method
		psycopg.adapters.register_loader("timestamptz", SafeTimestamptzLoader)
		psycopg.adapters.register_loader("timestamp", SafeTimestampLoader)
	except Exception as e: lg.warning(f"Failed to register custom timestamp loaders: {e}")



def init():
	try:
		from pillow_heif import register_heif_opener
		register_heif_opener()
	except ImportError:
		register_heif_opener = None
		lg.info("pillow-heif not available, skipping HEIC/HEIF support")

	# Setup custom timestamp loaders to handle BC dates
	setup_safe_timestamp_loader()

	host = envs.psqlHost
	port = envs.psqlPort
	db = envs.psqlDb
	uid = envs.psqlUser

	if not all([host, port, db, uid]): raise RuntimeError("PostgreSQL connection settings not initialized.")

	try:
		with mkConn() as conn:
			with conn.cursor() as cursor: cursor.execute("SELECT 1")

		# Detect schema after connection is verified
		detectSchema()

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
			with conn.cursor() as c: c.execute("SELECT 1")
		return True
	except Exception as e: raise mkErr("Failed to connect to PostgreSQL", e)


def fetchUser(usrId: str) -> Optional[models.Usr]:
	try:
		sch = getSchema()
		with mkConn() as conn:
			q = Q(f'Select id, name, email From "{sch.user}" Where id = %s')
			with conn.cursor(row_factory=dict_row) as cursor:
				cursor.execute(q, (usrId,))
				row = cursor.fetchone()

				if not row: raise RuntimeError("no db row")

				return models.Usr.fromDic(row)
	except Exception as e: raise mkErr(f"Failed to fetch userId[{usrId}]", e)

def fetchLibraries() -> List[models.Library]:
	try:
		chk()
		with mkConn() as conn:
			with conn.cursor(row_factory=dict_row) as cursor:
				cursor.execute(Q('Select id, name, "ownerId", "importPaths" From library'))
				rows = cursor.fetchall()
				return [models.Library.fromDic(dict(r)) for r in rows]
	except Exception as e: raise RuntimeError(f"Failed to fetch libraries: {e}")


def fetchUsers() -> List[models.Usr]:
	try:
		sch = getSchema()
		with mkConn() as conn:
			q = Q(f'Select id, name, email From "{sch.user}"')
			with conn.cursor(row_factory=dict_row) as cursor:
				cursor.execute(q)
				dics = cursor.fetchall()
				usrs = [models.Usr.fromDic(d) for d in dics]

				nams = []
				for u in usrs: nams.append(u.name)

				lg.info(f"[psql] fetch users[{len(usrs)}] {nams}")

				return usrs
	except Exception as e: raise mkErr("Failed to fetch users", e)


def count(usrId=None, assetType="IMAGE"):
	try:
		sch = getSchema()
		with mkConn() as conn:
			with conn.cursor() as cursor:
				q = f"Select Count(*) From {sch.asset} Where 1=1"
				params = []

				if assetType:
					q += " AND type = %s"
					params.append(assetType)

				if usrId:
					q += ' AND "ownerId" = %s'
					params.append(usrId)

				q += " AND status = 'active'"

				cursor.execute(Q(q), params)
				rst = cursor.fetchone()
				cnt = rst[0] if rst else 0

				return cnt
	except Exception as e: raise mkErr("Failed to count assets", e)



def testAssetsPath():
	try:
		with mkConn() as conn:
			sch = getSchema()
			sql = Q(f"Select path From {sch.assetFile} Limit 5")
			with conn.cursor(row_factory=dict_row) as cursor:
				cursor.execute(sql)
				rows = cursor.fetchall()

				if not rows or not len(rows): return "No Assets"

				for row in rows:
					pathDB = row.get("path", "")
					if pathDB:
						originalPath = pathDB
						isThumb = '/thumbs/' in pathDB or pathDB.startswith('thumbs/')
						pathFi = rtm.pth.full(pathDB)

						existsFi = os.path.exists(pathFi)
						lg.info(f"[psql] testPath: DB[{originalPath}] → full[{pathFi}] exists[{existsFi}] isThumb[{isThumb}]")
						if isThumb: lg.info(f"[psql] testPath: IMMICH_THUMB env[{envs.envImmichThumb or '(not set)'}] → cont[{envs.immichThumb or '(not set)'}]")

						if existsFi:
							lg.info(f"[psql] testPath: OK")
							return ["OK"]

						# Docker mode: try host path mapping
						if envs.isDock and envs.envImmichPath:
							hostPth = envs.envImmichPath.rstrip('/')
							contPth = rtm.immichPath.rstrip('/')
							lg.info(f"[psql] testPath: trying mapping host[{hostPth}] → cont[{contPth}]")

							if originalPath.startswith(hostPth + '/') or originalPath == hostPth:
								mappedPath = originalPath.replace(hostPth, contPth, 1)
								lg.info(f"[psql] testPath: mapped[{mappedPath}] exists[{os.path.exists(mappedPath)}]")

								if os.path.exists(mappedPath):
									rtm.pathHostMap[hostPth] = contPth
									lg.info(f"[psql] Path mapping enabled: {hostPth} → {contPth}")
									return ["OK", f"Path mapping: {hostPth} → {contPth}"]

						# error message
						envVar = 'IMMICH_THUMB' if isThumb else 'IMMICH_PATH'
						if isThumb and not envs.immichThumb:
							lg.error(f"[psql] testPath: FAILED - thumb path detected but IMMICH_THUMB not configured")
							return [
								"Thumbnail path detected but IMMICH_THUMB not configured:",
								f"  DB path: '{originalPath}'",
								f"  Resolved: '{pathFi}' (not found)",
								"",
								"For separate thumbnail directory, set IMMICH_THUMB in .env",
								"and add volume mount: - ${IMMICH_THUMB}:/thumbs:ro"
							]

						lg.error(f"[psql] testPath: FAILED - {envVar} path not found [{pathFi}]")
						return [
							"Asset file not found at expected path:",
							f"  {pathFi}",
							"",
							"This path was constructed from:",
							f"  {envVar} + DB Path",
							f"  DB Path: '{originalPath}'",
							"",
							f"Please verify {envVar} environment variable matches your Immich installation path."
						]

				return [
					"Asset path test failed.",
					"Unable to find any accessible asset files.",
				]
	except Exception as e: raise mkErr("Failed to test assets path. Please verify IMMICH_PATH/IMMICH_THUMB environment variables match your Immich installation paths", e)



def fetchAssets(usr: models.Usr, onUpdate: models.IFnProg):
	usrId = usr.id
	asType = "IMAGE"

	try:
		chk()

		onUpdate(11, f"start querying {usrId}")

		with mkConn() as conn:
			with conn.cursor(row_factory=dict_row) as cursor:
				# count all
				sch = getSchema()
				cntQ = f"Select Count( * ) From {sch.asset} Where status = 'active' And type = %s"
				cntArs = [asType]

				if usrId:
					cntQ += " AND \"ownerId\" = %s"
					cntArs.append(usrId)

				cursor.execute(Q(cntQ), cntArs)
				rst = cursor.fetchone()
				if not rst: raise RuntimeError("cannot count assets")

				cntAll = rst.get("count", 0)

				if not cntAll: raise RuntimeError(f"fetch target type[{asType}] not found")

				# lg.info(f"Found {cntAll} {asType.lower()} assets...")
				onUpdate(15, f"start querying {cntAll}")

				#----------------------------------------------------------------
				# query assets
				#----------------------------------------------------------------
				assetQ = f"Select * From {sch.asset} Where status = 'active' And type = %s"

				params = [asType]

				if usrId:
					assetQ += " AND \"ownerId\" = %s"
					params.append(usrId)

				assetQ += " ORDER BY \"createdAt\" DESC"

				cursor.execute(Q(assetQ), params)

				szBatch = 100
				szChunk = 100
				assets = []
				cntFetched = 0

				# tStart = time.time()

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
				flsSql = Q(f'Select "assetId", type, path From {sch.assetFile} Where "assetId" = ANY(%s)')
				assetIds = [a['id'] for a in assets]
				afs = []

				for idx, i in enumerate(range(0, len(assetIds), szChunk)):
					chunk = assetIds[i:i + szChunk]
					cursor.execute(flsSql, (chunk,))
					chunkRows = cursor.fetchall()
					afs.extend(chunkRows)

					# chunkPct = min((idx + 1) * szChunk, len(assetIds))

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
				exifSql = Q(f'Select * From {sch.assetExif} Where "assetId" = ANY(%s)')

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
								if isinstance(val, str): exifItem[key] = val
								else: exifItem[key] = val.isoformat() if val else None
							elif val is not None: exifItem[key] = val

						if exifItem: exifData[assetId] = exifItem

					# chunkPct = min((idx + 1) * szChunk, len(assetIds))

				#----------------------------------------------------------------
				# query livephoto videos
				#----------------------------------------------------------------
				onUpdate(42, "query livephoto videos...")

				livePhotoQ = Q(f"""
					-- Method 1: Direct livePhotoVideoId
					SELECT
						a.id AS photo_id,
						a."livePhotoVideoId" AS video_id,
						v."encodedVideoPath" AS video_path,
						v."originalPath" AS video_original_path
					FROM {sch.asset} a
					JOIN {sch.asset} v ON v.id = a."livePhotoVideoId" AND v.type = 'VIDEO'
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
					FROM {sch.asset} a
					JOIN {sch.assetExif} ae ON a.id = ae."assetId"
					JOIN {sch.assetExif} ve ON ae."livePhotoCID" = ve."livePhotoCID"
					JOIN {sch.asset} v ON ve."assetId" = v.id
					WHERE ae."livePhotoCID" IS NOT NULL
					AND a."livePhotoVideoId" IS NULL
					AND a.type = 'IMAGE'
					AND v.type = 'VIDEO'
					AND v.id != a.id
					AND a.id = ANY(%s)
				""")

				livePaths = {}
				liveVdoIds = {}
				for idx, i in enumerate(range(0, len(assetIds), szChunk)):
					chunk = assetIds[i:i + szChunk]
					cursor.execute(livePhotoQ, (chunk, chunk))
					chunkRows = cursor.fetchall()

					for row in chunkRows:
						photoId = row['photo_id']
						videoId = row['video_id']
						videoPath = row['video_path']
						originalVideoPath = row['video_original_path']

						finalPath = videoPath if videoPath else originalVideoPath
						if finalPath:
							livePaths[photoId] = rtm.pth.normalize(finalPath)
							liveVdoIds[photoId] = videoId

				#----------------------------------------------------------------
				# combine & fetch thumbnail image
				#----------------------------------------------------------------
				onUpdate(45, "files ready, combine data...")

				cntOk = 0
				noThumbIds = []
				noExifIds = []

				rst = []

				for asset in assets:
					assetId = asset['id']
					if assetId in dictFiles:
						for typ, path in dictFiles[assetId].items():
							if typ == ks.db.thumbnail: asset['thumbnail_path'] = rtm.pth.normalize(path)
							elif typ == ks.db.preview: asset['preview_path'] = rtm.pth.normalize(path)

					if assetId in livePaths: asset['video_path'] = livePaths[assetId]
					if assetId in liveVdoIds: asset['video_id'] = liveVdoIds[assetId]

					if assetId in exifData: asset['exifInfo'] = exifData[assetId]
					else: noExifIds.append(assetId)

					# final check
					pathThumbnail = asset.get('thumbnail_path')
					if not pathThumbnail:
						noThumbIds.append(assetId)
						continue

					cntOk += 1
					rst.append(asset)

					# if len(assets) > 0 and (cntOk % 100 == 0 or cntOk == len(assets)):
					#     report("combine", cntOk, len(assets), f"processing {cntOk}/{len(assets)}...")

				if noExifIds: lg.warn(f"[exif] NotFound for {len(noExifIds)} assets")
				if noThumbIds: lg.warn(f"[psql] ignored {len(noThumbIds)} assets without thumbnail")

				lg.info(f"Successfully fetched {len(rst)} {asType.lower()} assets")
				onUpdate(5, f"Successfully fetched {len(rst)} {asType.lower()} assets")

				return rst
	except Exception as e:
		msg = f"Failed to FetchAssets: {str(e)}"
		raise mkErr(msg, e)


#------------------------------------------------------
def fetchExInfo(assetId: str) -> Optional[models.AssetExInfo]:
	rst = fetchExInfos([assetId])
	return rst.get(assetId)


def fetchExInfos(assetIds: List[str]) -> Dict[str, models.AssetExInfo]:
	if not assetIds: return {}

	try:
		sch = getSchema()
		with mkConn() as conn:
			with conn.cursor(row_factory=dict_row) as cursor:
				rst = {}
				szChunk = 100

				for assetId in assetIds: rst[str(assetId).strip()] = models.AssetExInfo()

				# Fetch visibility and exif (rating, description, location)
				for i in range(0, len(assetIds), szChunk):
					chunk = assetIds[i:i + szChunk]
					visQ = Q(f'''
					Select a.id, a.visibility, e.rating, e.description, e.latitude, e.longitude, e.city, e.state, e.country
					From {sch.asset} a
					Left Join {sch.assetExif} e On a.id = e."assetId"
					Where a.id = ANY(%s)
					''')
					cursor.execute(visQ, (chunk,))
					visRows = cursor.fetchall()
					for row in visRows:
						assetId = str(row['id']).strip()
						if assetId in rst:
							rst[assetId].visibility = row['visibility'] or 'timeline'
							rst[assetId].rating = row['rating'] or 0
							rst[assetId].description = row['description']
							rst[assetId].latitude = row['latitude']
							rst[assetId].longitude = row['longitude']
							rst[assetId].city = row['city']
							rst[assetId].state = row['state']
							rst[assetId].country = row['country']

				# stack
				stkMap = {}
				for i in range(0, len(assetIds), szChunk):
					chunk = assetIds[i:i + szChunk]
					stkQ = Q(f'Select id, "stackId" From {sch.asset} Where id = ANY(%s) And "stackId" Is Not Null')
					cursor.execute(stkQ, (chunk,))
					for row in cursor.fetchall(): stkMap[str(row['id']).strip()] = str(row['stackId'])

				if stkMap:
					uniqStkIds = list(set(stkMap.values()))
					stkMembers = {}
					for i in range(0, len(uniqStkIds), szChunk):
						chunk = uniqStkIds[i:i + szChunk]
						memQ = Q(f'''Select id, "stackId" From {sch.asset} Where "stackId" = ANY(%s) And status = 'active' ''')
						cursor.execute(memQ, (chunk,))
						for row in cursor.fetchall():
							sid = str(row['stackId'])
							if sid not in stkMembers: stkMembers[sid] = []
							stkMembers[sid].append(str(row['id']))

					for assetId, stkId in stkMap.items():
						if assetId in rst and stkId in stkMembers: rst[assetId].stackAssets = stkMembers[stkId]

				# albums
				for i in range(0, len(assetIds), szChunk):
					chunk = assetIds[i:i + szChunk]
					albQ = Q(f"""
					Select aaa."{sch.albumAssetAssetId}", a.id, a."ownerId", a."albumName", a.description,
							a."createdAt", a."updatedAt", a."albumThumbnailAssetId", a."isActivityEnabled", a."order"
					From {sch.album} a
					Join {sch.albumAsset} aaa On a.id = aaa."{sch.albumAssetAlbumId}"
					Where aaa."{sch.albumAssetAssetId}" = ANY(%s) And a."deletedAt" Is Null
					Order By a."createdAt" Desc
					""")
					cursor.execute(albQ, (chunk,))
					albRows = cursor.fetchall()
					# lg.info(f"Album query returned {len(albRows)} rows for chunk {chunk}")

					for row in albRows:
						assetId = str(row[sch.albumAssetAssetId]).strip()
						if assetId in rst:
							albData = {k: v for k, v in row.items() if k != sch.albumAssetAssetId}
							rst[assetId].albs.append(models.Album.fromDic(albData))

				# tags
				for i in range(0, len(assetIds), szChunk):
					chunk = assetIds[i:i + szChunk]
					tagQ = Q(f"""
					Select ta."{sch.tagAssetAssetId}", t.id, t.value, t."userId"
					From {sch.tag} t
					Join {sch.tagAsset} ta On t.id = ta."{sch.tagAssetTagId}"
					Where ta."{sch.tagAssetAssetId}" = ANY(%s)
					""")
					cursor.execute(tagQ, (chunk,))
					tagRows = cursor.fetchall()

					for row in tagRows:
						assetId = str(row[sch.tagAssetAssetId]).strip()
						if assetId in rst:
							tagData = {k: v for k, v in row.items() if k != sch.tagAssetAssetId}
							rst[assetId].tags.append(models.Tags.fromDic(tagData))

				# faces
				for i in range(0, len(assetIds), szChunk):
					chunk = assetIds[i:i + szChunk]
					facSql = Q(f"""
					Select af."assetId", af.id, af."personId", p.name, p."ownerId",
							af."imageWidth", af."imageHeight", af."boundingBoxX1", af."boundingBoxY1",
							af."boundingBoxX2", af."boundingBoxY2", af."sourceType"
					From {sch.assetFace} af
					Join person p On af."personId" = p.id
					Where af."assetId" = ANY(%s) And af."deletedAt" Is Null
					""")
					cursor.execute(facSql, (chunk,))
					facRows = cursor.fetchall()

					for row in facRows:
						assetId = str(row['assetId']).strip()
						if assetId in rst:
							facData = {k: v for k, v in row.items() if k != 'assetId'}
							rst[assetId].facs.append(models.AssetFace.fromDic(facData))


				return rst
	except Exception as e: raise mkErr(f"Failed to fetch extended info for assetIds[{len(assetIds)}]", e)


def exInfoFill(rst: List[models.Asset]):
	if not rst: return

	assetIds = [str(asset.id) for asset in rst]
	exInfos = fetchExInfos(assetIds)

	for asset in rst:
		assetId = str(asset.id)
		asset.ex = exInfos.get(assetId)
