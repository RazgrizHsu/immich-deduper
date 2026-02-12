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

pathDb = envs.ddupData + 'pics.db'


@contextmanager
def mkConn():
	"""Context manager for database connections"""
	conn = None
	try:
		conn = sqlite3.connect(pathDb, check_same_thread=False, timeout=30.0)
		conn.row_factory = sqlite3.Row
		conn.execute("PRAGMA foreign_keys = ON")
		conn.execute("PRAGMA busy_timeout=30000")
		conn.execute("PRAGMA synchronous=NORMAL")
		conn.execute("PRAGMA temp_store=MEMORY")
		yield conn
	finally:
		if conn: conn.close()



_SCHEMAS = {
	'assets': '''
		autoId           INTEGER Primary Key AUTOINCREMENT,
		id               TEXT Unique,
		ownerId          TEXT,
		deviceId         TEXT,
		libId            TEXT,
		type             TEXT,
		originalFileName TEXT,
		originalPath     TEXT,
		sidecarPath      TEXT,
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
		simOk            INTEGER Default 0
	''',
	'assetsGrps': '''
		autoId   INTEGER NOT NULL REFERENCES assets(autoId) ON DELETE CASCADE,
		groupId  INTEGER NOT NULL REFERENCES assets(autoId) ON DELETE CASCADE,
		isMain   INTEGER DEFAULT 0,
		PRIMARY KEY (autoId, groupId)
	''',
	'assetsSims': '''
		autoId   INTEGER NOT NULL REFERENCES assets(autoId) ON DELETE CASCADE,
		simAid   INTEGER NOT NULL REFERENCES assets(autoId) ON DELETE CASCADE,
		score    REAL NOT NULL,
		isSelf   INTEGER DEFAULT 0,
		PRIMARY KEY (autoId, simAid)
	''',
	'libraries': '''
		id          TEXT Primary Key,
		name        TEXT,
		ownerId     TEXT,
		importPaths TEXT Default '[]'
	''',
}

# auto-key columns: autoId (AUTOINCREMENT) and PRIMARY KEY columns
_AUTO_COLS = {'autoId'}


def _migrateCols(c, tbl, schema):
	c.execute(f"PRAGMA table_info({tbl})")
	existCols = {row[1] for row in c.fetchall()}
	tmpTbl = f"_mig_{tbl}"
	c.execute(f"Create Temp Table {tmpTbl} ({schema})")
	c.execute(f"PRAGMA temp.table_info({tmpTbl})")
	for row in c.fetchall():
		col, typ, defVal = row[1], row[2], row[4]
		if col not in _AUTO_COLS and col not in existCols:
			colDef = f"{col} {typ}" + (f" Default {defVal}" if defVal is not None else "")
			c.execute(f"ALTER TABLE {tbl} ADD COLUMN {colDef}")
			lg.info(f"[pics:migration] added {tbl}.{col}")
	c.execute(f"Drop Table {tmpTbl}")



def _migrateSims(conn):
	c = conn.cursor()

	c.execute("SELECT * FROM assets")
	assetRows = c.fetchall()
	assetCols = [desc[0] for desc in c.description]

	# column names
	newCols = {line.strip().split()[0] for line in _SCHEMAS['assets'].split(',') if line.strip()}
	dropCols = {'simGIDs', 'simInfos', 'simCnt'}
	keepCols = [col for col in assetCols if col not in dropCols and col in newCols]
	keepIdxs = [assetCols.index(col) for col in keepCols]

	grpsData = []  # [(autoId, groupId, isMain), ...]
	simsData = []  # [(autoId, simAid, score, isSelf), ...]

	aidIdx = assetCols.index('autoId')
	gidsIdx = assetCols.index('simGIDs') if 'simGIDs' in assetCols else None
	infosIdx = assetCols.index('simInfos') if 'simInfos' in assetCols else None

	for row in assetRows:
		autoId = row[aidIdx]

		if gidsIdx is not None and row[gidsIdx]:
			gids = json.loads(row[gidsIdx]) if row[gidsIdx] != '[]' else []
			for gid in gids:
				isMain = 1 if autoId == gid else 0
				grpsData.append((autoId, gid, isMain))

		if infosIdx is not None and row[infosIdx]:
			infos = json.loads(row[infosIdx]) if row[infosIdx] != '[]' else []
			for info in infos: simsData.append((autoId, info['aid'], info['score'], 1 if info.get('isSelf') else 0))

	lg.info(f"[pics:migration] read {len(assetRows)} assets, {len(grpsData)} grps, {len(simsData)} sims")

	lg.info("[pics:migration] dropping all tables...")
	c.execute("PRAGMA foreign_keys = OFF")
	for tbl in ['assetsSims', 'assetsGrps', 'assets', 'libraries']: c.execute(f"DROP TABLE IF EXISTS {tbl}")

	lg.info("[pics:migration] recreating tables...")
	for tbl, schema in _SCHEMAS.items(): c.execute(f"CREATE TABLE {tbl} ({schema})")

	lg.info("[pics:migration] inserting assets...")
	placeholders = ','.join(['?' for _ in keepCols])
	c.executemany(f"INSERT INTO assets ({','.join(keepCols)}) VALUES ({placeholders})", [tuple(row[i] for i in keepIdxs) for row in assetRows])

	if grpsData:
		lg.info("[pics:migration] inserting assetsGrps...")
		c.executemany("INSERT INTO assetsGrps (autoId, groupId, isMain) VALUES (?, ?, ?)", grpsData)

	if simsData:
		lg.info("[pics:migration] inserting assetsSims...")
		c.executemany("INSERT INTO assetsSims (autoId, simAid, score, isSelf) VALUES (?, ?, ?, ?)", simsData)

	c.execute("PRAGMA foreign_keys = ON")
	lg.info(f"[pics:migration] done: {len(assetRows)} assets, {len(grpsData)} grps, {len(simsData)} sims")


def init():
	try:
		with mkConn() as conn:
			c = conn.cursor()

			c.execute("PRAGMA table_info(assets)")
			cols = {row[1] for row in c.fetchall()}

			if 'simGIDs' in cols or 'simInfos' in cols:
				_migrateSims(conn)
				conn.commit()
			else:
				for tbl, schema in _SCHEMAS.items():
					c.execute(f"CREATE TABLE IF NOT EXISTS {tbl} ({schema})")
					if tbl == 'assets': _migrateCols(c, tbl, schema)

			c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_autoId_simOk ON assets(autoId, simOk)''')
			c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_isVectored ON assets(isVectored)''')
			c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_simOk ON assets(simOk)''')
			c.execute('''CREATE INDEX IF NOT EXISTS idx_assets_id ON assets(id)''')

			c.execute('''CREATE INDEX IF NOT EXISTS idx_ass_grp_groupId ON assetsGrps(groupId)''')
			c.execute('''CREATE INDEX IF NOT EXISTS idx_ass_grp_isMain ON assetsGrps(isMain) WHERE isMain = 1''')

			c.execute('''CREATE INDEX IF NOT EXISTS idx_ass_sim_simAid ON assetsSims(simAid)''')
			c.execute('''CREATE INDEX IF NOT EXISTS idx_ass_sim_score ON assetsSims(autoId, score DESC)''')

			conn.commit()

			lg.info(f"[pics] db connected: {pathDb}")

		return True
	except Exception as e: raise mkErr("Failed to initialize pics database", e)

def clearAll():
	try:
		with mkConn() as conn:
			c = conn.cursor()
			for tbl in reversed(list(_SCHEMAS.keys())): c.execute(f"Drop Table If Exists {tbl}")
			conn.commit()
		return init()
	except Exception as e: raise mkErr("Failed to clear pics database", e)


def upsertLibraries(libraries: list):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			for lib in libraries:
				paths = json.dumps(lib.get('importPaths', []))
				c.execute('''
					Insert Into libraries (id, name, ownerId, importPaths)
					Values (?, ?, ?, ?)
					On Conflict(id) Do Update Set
						name = excluded.name,
						ownerId = excluded.ownerId,
						importPaths = excluded.importPaths
				''', (lib['id'], lib.get('name'), lib.get('ownerId'), paths))
			conn.commit()
			return len(libraries)
	except Exception as e: raise mkErr("Failed to upsert libraries", e)


def getLibraries() -> list:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("Select * From libraries")
			rows = c.fetchall()
			result = []
			for row in rows:
				lib = dict(row)
				lib['importPaths'] = json.loads(lib.get('importPaths', '[]'))
				result.append(lib)
			return result
	except Exception as e: raise mkErr("Failed to get libraries", e)


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
	except Exception as e: raise mkErr(f"Failed to delete assets by userId[{usrId}]", e)


def count(usrId=None):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			sql = "Select Count(*) From assets"
			if usrId:
				sql += " Where ownerId = ?"
				c.execute(sql, (usrId,))
			else: c.execute(sql)
			cnt = c.fetchone()[0]
			return cnt
	except Exception as e: raise mkErr("Failed to get assets count", e)


#========================================================================
# quary
#========================================================================
def getByAutoId(autoId) -> models.Asset:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
				SELECT a.*,
					GROUP_CONCAT(DISTINCT ag.groupId) as _simGIDs,
					(SELECT json_group_array(json_object('aid', simAid, 'score', score, 'isSelf', isSelf))
					FROM (SELECT simAid, score, isSelf FROM assetsSims WHERE autoId = a.autoId ORDER BY score DESC)
					) as _simInfosJson
				FROM assets a
				LEFT JOIN assetsGrps ag ON a.autoId = ag.autoId
				WHERE a.autoId = ?
				GROUP BY a.autoId
			""", (autoId,))
			row = c.fetchone()

			if not row: raise RuntimeError(f"not found aid[{autoId}]")

			asset = models.Asset.fromDB(c, row)
			_fillSimFields(asset, row)
			return asset
	except Exception as e: raise mkErr("Failed to get asset by autoId", e)


def _fillSimFields(asset: models.Asset, row):
	"""Fill simGIDs and simInfos from query result"""
	simGIDsStr = row['_simGIDs'] if '_simGIDs' in row.keys() else None
	asset.simGIDs = [int(x) for x in simGIDsStr.split(',')] if simGIDsStr else []

	simInfosJson = row['_simInfosJson'] if '_simInfosJson' in row.keys() else None
	infos = json.loads(simInfosJson) if simInfosJson else []
	asset.simInfos = [
		models.SimInfo(aid=x['aid'], score=x['score'], isSelf=bool(x['isSelf']))
		for x in infos
	]


def getById(assId) -> models.Asset:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
			SELECT a.*,
				GROUP_CONCAT(DISTINCT ag.groupId) as _simGIDs,
				(SELECT json_group_array(json_object('aid', simAid, 'score', score, 'isSelf', isSelf))
				FROM (SELECT simAid, score, isSelf FROM assetsSims WHERE autoId = a.autoId ORDER BY score DESC)
				) as _simInfosJson
			FROM assets a
			LEFT JOIN assetsGrps ag ON a.autoId = ag.autoId
			WHERE a.id = ?
			GROUP BY a.autoId
			""", (assId,))
			row = c.fetchone()
			if not row: raise RuntimeError(f"NotFound id[{assId}]")
			asset = models.Asset.fromDB(c, row)
			_fillSimFields(asset, row)
			return asset
	except Exception as e: raise mkErr("Failed to get asset by id", e)


def getAllByUsrId(usrId: str) -> List[models.Asset]:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute(f"Select * From assets Where ownerId = ? ", (usrId,))
			rows = c.fetchall()
			if not rows: return []
			assets = [models.Asset.fromDB(c, row) for row in rows]
			return assets
	except Exception as e: raise mkErr(f"Failed to get assets by userId[{usrId}]", e)


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
	except Exception as e: raise mkErr(f"Failed to get assets by ids[{ids}]", e)


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
	except Exception as e: raise mkErr("Failed to get all assets", e)


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
	except Exception as e: raise mkErr("Failed to get non-vector assets", e)


#------------------------------------------------------------------------
# paged
#------------------------------------------------------------------------
def countFiltered(usrId="", opts="all", search="", pathFilter="", favOnly=False, arcOnly=False, liveOnly=False):
	try:
		cds = []
		pms = []

		if usrId:
			cds.append("ownerId = ?")
			pms.append(usrId)

		if favOnly: cds.append("isFavorite = 1")

		if arcOnly: cds.append("isArchived = 1")

		if liveOnly: cds.append("vdoId IS NOT NULL")

		if opts == "with_vectors": cds.append("isVectored = 1")
		elif opts == "without_vectors": cds.append("isVectored = 0")

		if search and len(search.strip()) > 0:
			cds.append("originalFileName LIKE ?")
			pms.append(f"%{search}%")

		if pathFilter and len(pathFilter.strip()) > 0:
			cds.append("originalPath LIKE ?")
			pms.append(f"%{pathFilter}%")

		query = "Select Count(*) From assets"
		if cds: query += " WHERE " + " AND ".join(cds)

		with mkConn() as conn:
			cursor = conn.cursor()
			cursor.execute(query, pms)
			return cursor.fetchone()[0]
	except Exception as e:
		lg.error(f"Error counting assets: {str(e)}")
		return 0


def getFiltered(usrId="", opts="all", search="", pathFilter="", onlyFav=False, onlyArc=False, onlyLive=False, page=1, pageSize=24) -> list[models.Asset]:
	try:
		cds = []
		pms = []

		if usrId:
			cds.append("a.ownerId = ?")
			pms.append(usrId)

		if onlyFav: cds.append("a.isFavorite = 1")

		if onlyArc: cds.append("a.isArchived = 1")

		if onlyLive: cds.append("a.vdoId IS NOT NULL")

		if opts == "with_vectors": cds.append("a.isVectored = 1")
		elif opts == "without_vectors": cds.append("a.isVectored = 0")

		if search and len(search.strip()) > 0:
			cds.append("a.originalFileName LIKE ?")
			pms.append(f"%{search}%")

		if pathFilter and len(pathFilter.strip()) > 0:
			cds.append("a.originalPath LIKE ?")
			pms.append(f"%{pathFilter}%")

		query = """
			SELECT a.*,
					GROUP_CONCAT(DISTINCT ag.groupId) as _simGIDs
			FROM assets a
			LEFT JOIN assetsGrps ag ON a.autoId = ag.autoId
		"""
		if cds: query += " WHERE " + " AND ".join(cds)

		query += f" GROUP BY a.autoId ORDER BY a.autoId DESC"
		query += f" LIMIT {pageSize} OFFSET {(page - 1) * pageSize}"

		with mkConn() as conn:
			cursor = conn.cursor()
			cursor.execute(query, pms)
			assets = []
			for row in cursor.fetchall():
				ass = models.Asset.fromDB(cursor, row)
				_fillSimFields(ass, row)
				assets.append(ass)

			psql.exInfoFill(assets)
			return assets
	except Exception as e:
		lg.error(f"Error fetching assets: {str(e)}")
		return []


#========================================================================
# update
#========================================================================

def setVectoredBy(asset: models.Asset, done=1, cur: Optional[Cursor]=None):
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
	except Exception as e: raise mkErr(f"Failed to update vector status for asset[{asset.id}]", e)


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
			except Exception as e: raise mkErr("[pics.save] Error converting EXIF to JSON", e)

		c.execute("Select originalPath, pathThumbnail, pathPreview, pathVdo, jsonExif, isFavorite, isArchived, libId From assets Where id = ?", (str(assId),))
		row = c.fetchone()

		if row is None:
			c.execute('''
				Insert Into assets (id, ownerId, deviceId, libId, vdoId, type, originalFileName, originalPath,
				sidecarPath, fileCreatedAt, fileModifiedAt, isFavorite, isArchived,
				localDateTime, pathThumbnail, pathPreview, pathVdo, jsonExif)
				Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				''', (
				str(assId),
				str(asset.get('ownerId')),
				asset.get('deviceId'),
				str(asset.get('libraryId')) if asset.get('libraryId') else None,
				str(asset.get('video_id')) if asset.get('video_id') else None,
				asset.get('type'),
				asset.get('originalFileName'),
				asset.get('originalPath'),
				asset.get('sidecarPath'),
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
		if row['libId'] != (str(asset.get('libraryId')) if asset.get('libraryId') else None): needUpdate = True

		if needUpdate:
			c.execute('''
			Update assets Set
				originalPath = ?,
				sidecarPath = ?,
				libId = ?,
				pathThumbnail = ?,
				pathPreview = ?,
				pathVdo = ?,
				jsonExif = ?,
				isFavorite = ?,
				isArchived = ?
			Where id = ?
			''', (
				asset.get('originalPath'),
				asset.get('sidecarPath'),
				str(asset.get('libraryId')) if asset.get('libraryId') else None,
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
	except Exception as e: raise mkErr("Failed to save asset", e)


#========================================================================
# sim
#========================================================================

def getAnyNonSim(exclAids=[]) -> Optional[models.Asset]:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			# assets without any assetsSims records (not searched yet)
			sql = """
				SELECT a.* FROM assets a
				WHERE a.isVectored = 1 AND a.simOk != 1
				AND NOT EXISTS (SELECT 1 FROM assetsSims si WHERE si.autoId = a.autoId)
			"""
			params = []

			if exclAids:
				qargs = ','.join(['?' for _ in exclAids])
				sql += f" AND a.autoId NOT IN ({qargs})"
				params.extend(exclAids)

			c.execute(sql, params)
			while True:
				row = c.fetchone()
				if row is None: return None
				asset = models.Asset.fromDB(c, row)

				import db
				if not db.dto.checkIsExclude(asset): return asset
	except Exception as e: raise mkErr("Failed to get non-sim asset", e)


def countSimOk(isOk=0):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("SELECT COUNT(*) FROM assets WHERE isVectored = 1 AND simOk = ?", (isOk,))
			count = c.fetchone()[0]
			# lg.info(f"[pics] count isOk[{isOk}] cnt[{count}]")
			return count
	except Exception as e: raise mkErr(f"Failed to count assets with simOk[{isOk}]", e)


def setSimGIDs(autoId: int, GID: int):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			isMain = 1 if autoId == GID else 0
			c.execute(
				"INSERT OR IGNORE INTO assetsGrps (autoId, groupId, isMain) VALUES (?, ?, ?)",
				(autoId, GID, isMain)
			)
			conn.commit()
			return c.rowcount > 0
	except Exception as e: raise mkErr(f"Failed to set simGIDs for asset[{autoId}]", e)


def hasSimGIDs(autoId: int) -> bool:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("SELECT 1 FROM assetsGrps WHERE autoId = ? LIMIT 1", (autoId,))
			return c.fetchone() is not None
	except Exception as e: raise mkErr(f"Failed to check simGIDs for asset[{autoId}]", e)


def setSimInfos(autoId: int, infos: List[models.SimInfo], isOk=0):
	if not infos or len(infos) <= 0: raise RuntimeError(f"Can't setSimInfos id[{autoId}] by [{type(infos)}], {tracebk.format_exc()}")

	try:
		with mkConn() as conn:
			c = conn.cursor()

			# clear old simInfos
			c.execute("DELETE FROM assetsSims WHERE autoId = ?", (autoId,))

			# insert new
			for info in infos:
				c.execute(
					"INSERT INTO assetsSims (autoId, simAid, score, isSelf) VALUES (?, ?, ?, ?)",
					(autoId, info.aid, info.score, 1 if info.isSelf else 0)
				)

			# update simOk
			c.execute("UPDATE assets SET simOk = ? WHERE autoId = ?", (isOk, autoId))

			conn.commit()
	except Exception as e: raise mkErr("Failed to set similar IDs", e)


def deleteBy(assets: List[models.Asset]):
	try:
		cntAll = len(assets)
		with mkConn() as conn:
			c = conn.cursor()

			aids = [ass.autoId for ass in assets]

			# get mainGIDs from assetsGrps
			qargs = ','.join(['?' for _ in aids])
			c.execute(f"""
				SELECT DISTINCT groupId FROM assetsGrps
				WHERE autoId IN ({qargs}) AND isMain = 1
			""", aids)
			mainGIDs = [row[0] for row in c.fetchall()]

			# 1. Delete from assets (FK CASCADE auto deletes assetsGrps and assetsSims)
			assIds = [ass.id for ass in assets]
			if not assIds: raise RuntimeError(f"No asset IDs found")

			qargs2 = ','.join(['?' for _ in assIds])
			c.execute(f"DELETE FROM assets WHERE id IN ({qargs2})", assIds)
			count = c.rowcount

			if count != cntAll: raise mkErr(f"Failed to delete assets({cntAll}) with affected[{count}]")

			# 2. Delete from vector database
			import db.vecs as vecs
			vecs.deleteBy(aids)

			# 3. Handle other assets' assetsSims referencing deleted assets
			for delAid in aids:
				# delete references in assetsSims
				c.execute("DELETE FROM assetsSims WHERE simAid = ?", (delAid,))

			# 4. Auto-resolve assets with only self remaining in assetsSims
			c.execute("""
				UPDATE assets SET simOk = 1
				WHERE simOk = 0 AND autoId IN (
					SELECT autoId FROM assetsSims
					GROUP BY autoId
					HAVING COUNT(*) = 1 AND MAX(isSelf) = 1
				)
			""")

			conn.commit()
			lg.info(f"[pics] delete by assIds[{cntAll}] rst[{count}] mainGIDs[{mainGIDs}]")

			return count
	except Exception as e: raise mkErr("Failed to delete assets", e)


def setResolveBy(assets: List[models.Asset]):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			autoIds = [ass.autoId for ass in assets]
			if not autoIds: return 0

			autoIds = list(set(autoIds))
			cnt = len(autoIds)

			qargs = ','.join(['?' for _ in autoIds])

			# delete from relation tables
			c.execute(f"DELETE FROM assetsGrps WHERE autoId IN ({qargs})", autoIds)
			c.execute(f"DELETE FROM assetsSims WHERE autoId IN ({qargs})", autoIds)

			# update simOk
			c.execute(f"UPDATE assets SET simOk = 1 WHERE autoId IN ({qargs})", autoIds)
			count = c.rowcount
			if count != cnt: raise RuntimeError(f"effect[{count}] not match assets[{cnt}] ids[{qargs}]")
			conn.commit()
			lg.info(f"[pics] set simOk by autoIds[{len(autoIds)}] rst[{count}]")
			return count
	except Exception as e: raise mkErr("Failed to resolve sim assets", e)


# noinspection SqlWithoutWhere
def clearAllSimIds(keepSimOk=False):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			if keepSimOk:
				# only clear simOk=0
				c.execute("""
					DELETE FROM assetsGrps
					WHERE autoId IN (SELECT autoId FROM assets WHERE simOk = 0)
				""")
				c.execute("""
					DELETE FROM assetsSims
					WHERE autoId IN (SELECT autoId FROM assets WHERE simOk = 0)
				""")
				lg.info(f"Cleared similarity search results but kept resolved items")
			else:
				c.execute("DELETE FROM assetsGrps")
				c.execute("DELETE FROM assetsSims")
				c.execute("UPDATE assets SET simOk = 0")
				lg.info(f"Cleared all similarity results")
			conn.commit()
			count = c.rowcount
			lg.info(f"Cleared similarity results for {count} assets")
			return count
	except Exception as e: raise mkErr("Failed to clear sim results", e)


def countHasSimIds(isOk=0):
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
				SELECT COUNT(*) FROM (
					SELECT si.autoId FROM assetsSims si
					INNER JOIN assets a ON si.autoId = a.autoId
					WHERE a.simOk = ?
					GROUP BY si.autoId
					HAVING COUNT(*) > 1
				)
			""", (isOk,))
			row = c.fetchone()
			count = row[0] if row else 0
			return count
	except Exception as e: raise mkErr(f"Failed to count assets with simInfos and simOk[{isOk}]", e)


# simOk mean that already resolve by user
def getAnySimPending() -> Optional[models.Asset]:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
				SELECT a.* FROM assets a
				WHERE a.simOk = 0
					AND (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) > 1
				LIMIT 1
			""")
			row = c.fetchone()
			return models.Asset.fromDB(c, row) if row else None
	except Exception as e: raise mkErr("Failed to get pending assets", e)


def getAllSimOks(isOk=0) -> List[models.Asset]:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
				SELECT a.* FROM assets a
				WHERE a.simOk = ?
					AND (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) > 1
				ORDER BY a.autoId
			""", (isOk,))
			rows = c.fetchall()
			if not rows: return []
			assets = [models.Asset.fromDB(c, row) for row in rows]
			return assets
	except Exception as e: raise mkErr("Failed to get all simOk assets", e)


# noinspection SqlWithoutWhere
def clearAllVectored():
	try:
		with mkConn() as cnn:
			c = cnn.cursor()
			c.execute("UPDATE assets SET isVectored=0")
			cnn.commit()
	except Exception as e: raise mkErr(f"Failed to set isVectored to 0", e)


# auto mark simOk=1 if simInfos only includes self
def setSimAutoMark():
	try:
		with mkConn() as cnn:
			c = cnn.cursor()
			c.execute("""
				UPDATE assets
				SET simOk = 1
				WHERE simOk = 0 AND autoId IN (
					SELECT autoId FROM assetsSims
					GROUP BY autoId
					HAVING COUNT(*) = 1 AND MAX(isSelf) = 1
				)
			""")
			cnn.commit()
	except Exception as e: raise mkErr(f"Failed execute SimAutoMark", e)


def getAssetsByGID(gid: int) -> list[models.Asset]:
	try:
		with mkConn() as conn:
			c = conn.cursor()
			c.execute("""
				SELECT a.* FROM assets a
				INNER JOIN assetsGrps ag ON a.autoId = ag.autoId
				WHERE ag.groupId = ?
					AND (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) > 1
				ORDER BY a.autoId
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

	rst = []

	try:
		with mkConn() as conn:
			c = conn.cursor()

			# query root asset with simGIDs and simInfos
			c.execute("""
				SELECT a.*,
						GROUP_CONCAT(DISTINCT ag.groupId) as _simGIDs,
						(SELECT json_group_array(json_object('aid', simAid, 'score', score, 'isSelf', isSelf))
						FROM (SELECT simAid, score, isSelf FROM assetsSims WHERE autoId = a.autoId ORDER BY score DESC)
						) as _simInfosJson,
						COALESCE(ag_main.isMain, 0) as _isMain
				FROM assets a
				LEFT JOIN assetsGrps ag ON a.autoId = ag.autoId
				LEFT JOIN assetsGrps ag_main ON a.autoId = ag_main.autoId AND ag_main.groupId = a.autoId
				WHERE a.autoId = ?
				GROUP BY a.autoId
			""", (autoId,))
			row = c.fetchone()
			if row is None: raise RuntimeError(f"[pics] SimGroup Root asset #{autoId} not found")

			root = models.Asset.fromDB(c, row)
			_fillSimFields(root, row)
			root.vw.isMain = bool(row['_isMain'])
			rst = [root]

			if not incGroup:
				if not root.simInfos or len(root.simInfos) <= 1: return rst

				simAids = [info.aid for info in root.simInfos if not info.isSelf]
				if not simAids: return [root]

				qargs = ','.join(['?' for _ in simAids])
				c.execute(f"""
					SELECT a.*,
							COALESCE(ag_main.isMain, 0) as _isMain
					FROM assets a
					LEFT JOIN assetsGrps ag_main ON a.autoId = ag_main.autoId AND ag_main.groupId = a.autoId
					WHERE a.autoId IN ({qargs})
				""", simAids)

				rows = c.fetchall()

				assets = []
				for row in rows:
					ass = models.Asset.fromDB(c, row)
					ass.vw.isMain = bool(row['_isMain'])
					ass.vw.score = next((info.score for info in root.simInfos if info.aid == ass.autoId), 0)
					assets.append(ass)

				assetMap = {asset.autoId: asset for asset in assets}

				sortAss = []
				for simInfo in sorted(root.simInfos, key=lambda x: x.score or 0, reverse=True):
					if simInfo.aid in assetMap: sortAss.append(assetMap[simInfo.aid])

				rst.extend(sortAss)
			else:
				if not root.simGIDs: return rst

				# Find all assets in the group via assetsGrps table
				gid_placeholders = ','.join(['?' for _ in root.simGIDs])
				c.execute(f"""
					SELECT DISTINCT a.*,
							COALESCE(ag_main.isMain, 0) as _isMain
					FROM assets a
					INNER JOIN assetsGrps ag ON a.autoId = ag.autoId
					LEFT JOIN assetsGrps ag_main ON a.autoId = ag_main.autoId AND ag_main.groupId = a.autoId
					WHERE a.autoId != ? AND (
						ag.groupId IN ({gid_placeholders})
						OR ag.groupId = ?
					)
				""", [autoId] + root.simGIDs + [root.autoId])
				rows = c.fetchall()

				if not rows: return rst

				assets = []
				for row in rows:
					ass = models.Asset.fromDB(c, row)
					ass.vw.isMain = bool(row['_isMain'])
					assets.append(ass)

				try:
					rootVec = vecs.getBy(root.autoId)
					rootVecNp = np.array(rootVec)

					rootSimAids = {info.aid for info in root.simInfos}

					assetIds = [ass.autoId for ass in assets]
					assVecs = vecs.getAllBy(assetIds)

					assScores = []
					for ass in assets:
						if ass.autoId not in assVecs:
							lg.warn(f"[pics] Vector not found for asset {ass.autoId}")
							continue

						assVecNp = np.array(assVecs[ass.autoId])
						score = np.dot(rootVecNp, assVecNp)

						ass.vw.isRelats = ass.autoId not in rootSimAids
						ass.vw.score = score

						assScores.append((ass, score))

					assScores.sort(key=lambda x: x[1], reverse=True)
					rst.extend([ass for ass, _ in assScores])
				except Exception as e:
					lg.error(f"[pics] Error processing vectors: {str(e)}")
					rst.extend(assets)

			psql.exInfoFill(rst)
			return rst
	except Exception as e: raise mkErr(f"Failed to get similar group for root #{autoId}", e)


def countSimPending():
	try:
		with mkConn() as conn:
			c = conn.cursor()
			# Count groups with isMain=1 and simOk=0 and more than 1 assetsSims
			c.execute("""
				SELECT COUNT(*) FROM assets a
				WHERE a.simOk = 0
					AND EXISTS (SELECT 1 FROM assetsGrps ag WHERE ag.autoId = a.autoId AND ag.isMain = 1)
					AND (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) > 1
			""")
			cnt = c.fetchone()[0]
			return cnt
	except Exception as e: raise mkErr(f"Failed to count assets pending", e)


def getPagedPending(page=1, size=20) -> list[models.Asset]:
	try:
		with mkConn() as conn:
			cursor = conn.cursor()
			offset = (page - 1) * size

			cursor.execute("""
				SELECT a.*,
						(SELECT json_group_array(json_object('aid', simAid, 'score', score, 'isSelf', isSelf))
						FROM (SELECT simAid, score, isSelf FROM assetsSims WHERE autoId = a.autoId ORDER BY score DESC)
						) as _simInfosJson,
						(SELECT COUNT(*) FROM assetsGrps ag2
						WHERE ag2.groupId IN (SELECT groupId FROM assetsGrps WHERE autoId = a.autoId)
							AND ag2.autoId != a.autoId) as cntRelats
				FROM assets a
				INNER JOIN assetsGrps ag ON a.autoId = ag.autoId AND ag.isMain = 1
				WHERE a.simOk = 0
					AND (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) > 1
				ORDER BY (SELECT COUNT(*) FROM assetsSims si WHERE si.autoId = a.autoId) DESC, a.autoId
				LIMIT ? OFFSET ?
			""", (size, offset))

			leaders = []
			for row in cursor.fetchall():
				asset = models.Asset.fromDB(cursor, row)
				_fillSimFields(asset, row)
				asset.vw.cntRelats = row['cntRelats']
				leaders.append(asset)

			return leaders
	except Exception as e:
		lg.error(f"Error fetching assets: {str(e)}")
		return []
