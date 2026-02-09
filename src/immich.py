import os
import shutil
from typing import List, Tuple, Optional
from dataclasses import dataclass

import requests
import re

from conf import ks
from util import log, err
from mod import models
from mod import bsh
import rtm

lg = log.get(__name__)

def getGithubRaw(url):
    url = url.replace('github.com', 'raw.githubusercontent.com')
    url = url.replace('/blob/', '/')

    try:
        # lg.info( f"[code] checking.. url[{url}]" )
        rep = requests.get(url)
        rep.raise_for_status()
        return rep.text
    except requests.exceptions.RequestException as e: raise RuntimeError(f"request url[{url}] failed: {e}")

def checkCodeBy(src, target_code):
    if not src: ValueError(f"src[{src}]")

    clean_src = re.sub(r'\s+', '', src).lower()
    clean_code = re.sub(r'\s+', '', target_code).lower()

    ok = clean_code in clean_src

    if not ok: lg.error(f"[checkCode] expect `{clean_code}` not in target: {clean_src}")

    return ok


url_delete = "https://github.com/immich-app/immich/blob/main/server/src/services/asset.service.ts"
code_deleteAll = """
    await this.assetRepository.updateAll(ids, {
      deletedAt: new Date(),
      status: force ? AssetStatus.DELETED : AssetStatus.TRASHED,
    })
"""

url_restore = "https://github.com/immich-app/immich/blob/main/server/src/repositories/trash.repository.ts"
code_Restore = """
  async restore(userId: string): Promise<number> {
    const { numUpdatedRows } = await this.db
      .updateTable('asset')
      .where('ownerId', '=', userId)
      .where('status', '=', assetstatus.trashed)
      .set({ status: assetstatus.active, deletedAt: null })
      .executeTakeFirst();
"""

def checkBy(url, code):
    src = getGithubRaw(url)
    if not src: raise RuntimeError(f"cannot fetch content from url[{url}]")

    ok = checkCodeBy(src, code)

    return ok

def checkLogicDelete(): return checkBy(url_delete, code_deleteAll)

def checkLogicRestore(): return checkBy(url_restore, code_Restore)



from db import psql

#------------------------------------------------------------------------
# Merge Schema Check
# - Check if Immich DB has asset_file table with correct structure for merge
#------------------------------------------------------------------------
_mergeOk = None
_mergeEx = None

def checkMergeSchema():
    global _mergeOk, _mergeEx

    if _mergeOk is not None: return _mergeOk, _mergeEx

    try:
        sch = psql.getSchema()
        with psql.mkConn() as conn:
            with conn.cursor() as cur:
                cur.execute(psql.Q(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = '{sch.assetFile}'
                    AND column_name IN ('assetId', 'type', 'path')
                """))
                cols = {row[0] for row in cur.fetchall()}
                required = {'assetId', 'type', 'path'}
                missing = required - cols

                if missing:
                    _mergeOk = False
                    _mergeEx = f"asset_file missing columns: {missing}"
                    lg.error(f"[merge:schema] {_mergeEx}")
                    return _mergeOk, _mergeEx

                _mergeOk = True
                _mergeEx = None
                lg.info(f"[merge:schema] OK - asset_file has required columns")
                return _mergeOk, _mergeEx
    except Exception as e:
        _mergeOk = False
        _mergeEx = str(e)
        lg.error(f"[merge:schema] Check failed: {_mergeEx}")
        return _mergeOk, _mergeEx


def isMergeAvailable():
    if _mergeOk is None: checkMergeSchema()
    return _mergeOk, _mergeEx


#------------------------------------------------------------------------
# delete
#
# This function moves multiple assets to trash by updating their status to 'trashed' and setting deletedAt timestamp
# Note: This implementation follows Immich's API flow which may change in future versions
# follow delete flow
# https://github.com/immich-app/immich/blob/main/server/src/services/asset.service.ts#L231
#------------------------------------------------------------------------
def trashBy(assetIds: List[str], cur):
    if not assetIds or len(assetIds) <= 0: raise RuntimeError(f"trashBy: assetIds is empty")

    sql = """
    Update "asset"
    Set "deletedAt" = Now(), status = %s
    Where id = ANY(%s)
    """
    cur.execute(sql, (ks.db.status.trashed, assetIds))
    return cur.rowcount

#------------------------------------------------------------------------
# delete by assets list
#------------------------------------------------------------------------
def trashByAssets(assets: List[models.Asset], cur):
    if not assets: return 0
    assetIds = [ass.id for ass in assets]
    return trashBy(assetIds, cur)


#------------------------------------------------------------------------
# Metadata Merge
#------------------------------------------------------------------------
@dataclass
class MergeOpts:
    albums: bool = False
    favorites: bool = False
    tags: bool = False
    rating: bool = False
    description: bool = False
    location: bool = False
    visibility: bool = False


def mergeMetadata(keepAssets: List[models.Asset], trashAssets: List[models.Asset], opts: MergeOpts, cur) -> dict:
    if not keepAssets or not trashAssets:
        lg.info(f"[merge] Skip: keepAssets[{len(keepAssets) if keepAssets else 0}] trashAssets[{len(trashAssets) if trashAssets else 0}]")
        return {'merged': False, 'reason': 'empty assets'}

    allAssets = keepAssets + trashAssets
    allIds = [a.id for a in allAssets]
    keepIds = [a.id for a in keepAssets]
    trashIds = [a.id for a in trashAssets]

    lg.info(f"[merge] ========== START ==========")
    lg.info(f"[merge] keepIds: {keepIds}")
    lg.info(f"[merge] trashIds: {trashIds}")
    lg.info(f"[merge] opts: albums={opts.albums} favorites={opts.favorites} tags={opts.tags} rating={opts.rating} description={opts.description} location={opts.location} visibility={opts.visibility}")

    result = {'merged': True, 'albums': 0, 'favorites': 0, 'tags': 0, 'rating': 0, 'description': 0, 'location': 0, 'visibility': 0}

    origExInfos = psql.fetchExInfos(allIds)
    sch = psql.getSchema()

    lg.info(f"[merge] ----- ORIGINAL STATE -----")
    for asset in allAssets:
        role = "KEEP" if asset.id in keepIds else "TRASH"
        ex = origExInfos.get(asset.id)
        lg.info(f"[merge] [{role}] id={asset.id} fav={asset.isFavorite} vis={ex.visibility if ex else 'timeline'}")
        lg.info(f"[merge]   albums={[a.id for a in ex.albs] if ex else []}")
        lg.info(f"[merge]   tags={[t.id for t in ex.tags] if ex else []}")
        lg.info(f"[merge]   rating={ex.rating if ex else 0} desc={ex.description[:50] if ex and ex.description else None}")
        lg.info(f"[merge]   lat={ex.latitude if ex else None} lng={ex.longitude if ex else None} city={ex.city if ex else None}")

    newEx = models.AssetExInfo()

    if opts.albums:
        for ex in origExInfos.values(): newEx.albs.extend([a for a in ex.albs if a.id not in [x.id for x in newEx.albs]])

    newFav = any(a.isFavorite for a in allAssets) if opts.favorites else False

    if opts.tags:
        for ex in origExInfos.values(): newEx.tags.extend([t for t in ex.tags if t.id not in [x.id for x in newEx.tags]])

    if opts.rating:
        for ex in origExInfos.values():
            if (ex.rating or 0) > newEx.rating: newEx.rating = ex.rating

    if opts.description:
        descSet, descLines = set(), []
        for ex in origExInfos.values():
            for line in (ex.description or '').split('\n'):
                trimmed = line.strip()
                if trimmed and trimmed not in descSet:
                    descSet.add(trimmed)
                    descLines.append(trimmed)
        newEx.description = '\n'.join(descLines) if descLines else None

    if opts.location:
        locCounts = {}
        for ex in origExInfos.values():
            if ex.latitude is not None and ex.longitude is not None:
                key = (ex.latitude, ex.longitude, ex.city, ex.state, ex.country)
                locCounts[key] = locCounts.get(key, 0) + 1
        if locCounts:
            best = max(locCounts.keys(), key=lambda k: locCounts[k])
            newEx.latitude, newEx.longitude, newEx.city, newEx.state, newEx.country = best

    if opts.visibility:
        visOrder = {'locked': 0, 'hidden': 1, 'archive': 2, 'timeline': 3}
        for asset in allAssets:
            ex = origExInfos.get(asset.id)
            vis = ex.visibility if ex else 'timeline'
            if visOrder.get(vis, 3) < visOrder.get(newEx.visibility, 3): newEx.visibility = vis

    lg.info(f"[merge] ----- NEW VALUES -----")
    lg.info(f"[merge] albums={[a.id for a in newEx.albs]} tags={[t.id for t in newEx.tags]}")
    lg.info(f"[merge] fav={newFav} vis={newEx.visibility} rating={newEx.rating}")
    lg.info(f"[merge] desc={newEx.description[:50] if newEx.description else None}")
    lg.info(f"[merge] lat={newEx.latitude} lng={newEx.longitude} city={newEx.city} state={newEx.state} country={newEx.country}")

    lg.info(f"[merge] ----- WRITING -----")

    # ========== Validate paths and permissions ==========
    xmpInfos = []  # [(asset, localPath, xmpPath, isNewXmp, bakPath)]
    for asset in keepAssets:
        localPath = rtm.pth.full(asset.originalPath)
        if not os.path.exists(localPath): raise FileNotFoundError(f"Merge failed: file not found - {localPath}")

        xmpPath = localPath + '.xmp'
        xmpDir = os.path.dirname(xmpPath)
        if not os.access(xmpDir, os.W_OK): raise PermissionError(f"Merge failed: no write permission - {xmpDir}")

        isNewXmp = not os.path.exists(xmpPath)
        bakPath = xmpPath + '.bak' if not isNewXmp else None
        xmpInfos.append((asset, localPath, xmpPath, isNewXmp, bakPath))

    # ========== Backup existing xmp files ==========
    for asset, localPath, xmpPath, isNewXmp, bakPath in xmpInfos:
        if not isNewXmp:
            origMeta = bsh.read(xmpPath)
            lg.info(f"[merge] original xmp: {asset.id} {origMeta}")
            shutil.move(xmpPath, bakPath)

    try:
        if opts.albums and newEx.albs:
            for alb in newEx.albs:
                cur.execute(psql.Q(f'''
                Insert Into {sch.albumAsset} ("{sch.albumAssetAlbumId}", "{sch.albumAssetAssetId}", "createdAt")
                Select %s, unnest(%s::uuid[]), Now()
                On Conflict Do Nothing
                '''), (alb.id, keepIds))
                result['albums'] += cur.rowcount
            lg.info(f"[merge] Albums: {result['albums']}")

        if opts.favorites and newFav:
            cur.execute(psql.Q(f'''
            Update {sch.asset} Set "isFavorite" = True, "updatedAt" = Now()
            Where id = ANY(%s)
            '''), (keepIds,))
            result['favorites'] = cur.rowcount
            lg.info(f"[merge] Favorites: {result['favorites']}")

        if opts.tags and newEx.tags:
            for tag in newEx.tags:
                cur.execute(psql.Q(f'''
                Insert Into {sch.tagAsset} ("{sch.tagAssetTagId}", "{sch.tagAssetAssetId}")
                Select %s, unnest(%s::uuid[])
                On Conflict Do Nothing
                '''), (tag.id, keepIds))
                result['tags'] += cur.rowcount
            lg.info(f"[merge] Tags: {result['tags']}")

        if opts.rating and newEx.rating > 0:
            cur.execute(psql.Q(f'''
            Update {sch.assetExif} Set rating = %s, "updatedAt" = Now()
            Where "assetId" = ANY(%s)
            '''), (newEx.rating, keepIds))
            result['rating'] = cur.rowcount
            lg.info(f"[merge] Rating: {result['rating']}")

        if opts.description and newEx.description:
            cur.execute(psql.Q(f'''
            Update {sch.assetExif} Set description = %s, "updatedAt" = Now()
            Where "assetId" = ANY(%s)
            '''), (newEx.description, keepIds))
            result['description'] = cur.rowcount
            lg.info(f"[merge] Description: {result['description']}")

        if opts.location and newEx.latitude is not None:
            cur.execute(psql.Q(f'''
            Update {sch.assetExif} Set
                latitude = %s, longitude = %s, city = %s, state = %s, country = %s,
                "updatedAt" = Now()
            Where "assetId" = ANY(%s)
            '''), (newEx.latitude, newEx.longitude, newEx.city, newEx.state, newEx.country, keepIds))
            result['location'] = cur.rowcount
            lg.info(f"[merge] Location: {result['location']}")

        if opts.visibility and newEx.visibility != 'timeline':
            cur.execute(psql.Q(f'''
            Update {sch.asset} Set visibility = %s, "updatedAt" = Now()
            Where id = ANY(%s)
            '''), (newEx.visibility, keepIds))
            result['visibility'] = cur.rowcount
            lg.info(f"[merge] Visibility: {result['visibility']}")

        # ========== Write xmp files ==========
        xmpTags = {}
        if opts.description and newEx.description:
            xmpTags['Description'] = newEx.description
            xmpTags['ImageDescription'] = newEx.description
        if opts.rating and newEx.rating > 0: xmpTags['Rating'] = newEx.rating
        if opts.location and newEx.latitude is not None:
            xmpTags['GPSLatitude'] = newEx.latitude
            xmpTags['GPSLongitude'] = newEx.longitude
        if opts.tags and newEx.tags: xmpTags['TagsList'] = [t.value for t in newEx.tags]

        if xmpTags:
            lg.info(f"[merge] xmpTags to write: {xmpTags}")
            for asset, localPath, xmpPath, isNewXmp, bakPath in xmpInfos:
                if not bsh.write(xmpPath, xmpTags): raise IOError(f"Merge failed: xmp write error - {xmpPath}")

                lg.info(f"[merge] xmp written: {xmpPath}")

                # Update sidecarPath for new xmp
                if isNewXmp:
                    dbXmpPath = asset.originalPath + '.xmp'
                    cur.execute(psql.Q(f'''
                        INSERT INTO {sch.assetFile} ("assetId", "type", "path")
                        VALUES (%s, 'sidecar', %s)
                        ON CONFLICT ("assetId", "type") DO UPDATE SET "path" = EXCLUDED."path"
                    '''), (asset.id, dbXmpPath))
                    lg.info(f"[merge] sidecarPath updated: {asset.id}")

        lg.info(f"[merge] ========== DB READY: {result} ==========")
        result['xmpInfos'] = xmpInfos
    except Exception as e:
        # Restore .bak files on rollback
        for asset, localPath, xmpPath, isNewXmp, bakPath in xmpInfos:
            if bakPath and os.path.exists(bakPath): shutil.move(bakPath, xmpPath)
            elif isNewXmp and os.path.exists(xmpPath): os.remove(xmpPath)
        lg.error(f"[merge] ========== ROLLBACK: {e} ==========")
        raise

    return result


def cleanupXmpBak(xmpInfos):
    for asset, localPath, xmpPath, isNewXmp, bakPath in xmpInfos:
        if bakPath and os.path.exists(bakPath): os.remove(bakPath)
    lg.info(f"[merge] ========== CLEANUP .bak DONE ==========")


def restoreXmpBak(xmpInfos):
    for asset, localPath, xmpPath, isNewXmp, bakPath in xmpInfos:
        if bakPath and os.path.exists(bakPath): shutil.move(bakPath, xmpPath)
        elif isNewXmp and os.path.exists(xmpPath): os.remove(xmpPath)
    lg.info(f"[merge] ========== RESTORE .bak DONE ==========")


def validateKeepPaths(assets: List[models.Asset]) -> List[str]:
    errs = []

    if not bsh.isInstalled():
        errs.append("exiftool CLI not found. Install with: brew install exiftool (macOS) or apt install exiftool (Linux)")
        return errs

    libNotFound = []
    immichNotFound = []
    noPermission = []

    for asset in assets:
        localPath = rtm.pth.full(asset.originalPath)
        dirPath = os.path.dirname(localPath)

        if not os.path.exists(localPath):
            if asset.libId: libNotFound.append((f"#{asset.autoId}", dirPath))
            else: immichNotFound.append((f"#{asset.autoId}", dirPath))
        elif not os.access(dirPath, os.W_OK): noPermission.append((f"#{asset.autoId}", dirPath))

    if libNotFound:
        items = [f"{aid} ({d})" for aid, d in libNotFound]
        errs.append(f"External Library files not found: {', '.join(items)}. Go to Fetch page to configure library paths.")
    if immichNotFound:
        items = [f"{aid} ({d})" for aid, d in immichNotFound]
        errs.append(f"Immich files not found: {', '.join(items)}. Check IMMICH_PATH setting.")
    if noPermission:
        items = [f"{aid} ({d})" for aid, d in noPermission]
        errs.append(f"No write permission: {', '.join(items)}")

    return errs
