import os
import shutil
from typing import Optional
from flask import send_file, request, make_response, jsonify
from flask_caching import Cache

from conf import envs, ks, pathCache
from util import log

lg = log.get(__name__)

enableCache = False

CacheBrowserSecs = 60 #暫時先不用, 頻繁換容易造成用到舊圖
TIMEOUT = (60 * 60 * 24) * 0.1  #day

dirCache = os.path.abspath(os.path.join(pathCache, 'imgs'))
cache:Optional[Cache] = None

def clear_cache():
    try:
        if cache:
            cache.clear()
        if os.path.exists(dirCache):
            shutil.rmtree(dirCache)
            os.makedirs(dirCache)
            lg.info(f"Cache directory cleared: {dirCache}")
        return True
    except Exception as e:
        lg.error(f"Error clearing cache: {str(e)}")
        return False

def getCache(ck, fnQ, mime='image/jpeg'):
    if not enableCache or not cache:
        path = fnQ()
        if not path:
            lg.warn(f"[serve] the db query failed with cache_key[ {ck} ]")
        else:
            pathFull = envs.pth.full(path)
            if not os.path.exists(pathFull):
                lg.warn(f"[serve] not exists path[ {pathFull} ]({path}) immichPath[ {envs.immichPath} ]")
            else:
                rep = make_response(send_file(pathFull, mimetype=mime))
                # rep.headers['Cache-Control'] = f'public, max-age={CacheBrowserSecs}'
                return rep
        return None

    data = cache.get(ck)

    if data is None:
        path = fnQ()
        if path:
            pathFull = envs.pth.full(path)
            if os.path.exists(pathFull):
                with open(pathFull, 'rb') as f: data = f.read()
                cache.set(ck, data)

    if data:
        from io import BytesIO
        rep = make_response(send_file(BytesIO(data), mimetype=mime))
        # rep.headers['Cache-Control'] = f'public, max-age={CacheBrowserSecs}'
        return rep

    return None



def regBy(app):
    import db
    global cache

    pathNoImg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets/noimg.png")

    cache = Cache(app.server, config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DIR': dirCache,
        'CACHE_DEFAULT_TIMEOUT': TIMEOUT,
        'CACHE_THRESHOLD': 300,
    })


    #----------------------------------------------------------------
    # serve for Image
    #----------------------------------------------------------------
    @app.server.route('/api/img/<aid>')
    def doGetImgBy(aid):
        try:
            photoQ = request.args.get('q', ks.db.thumbnail)
            cache_key = f"{aid}_{photoQ}"

            def query_image():
                with db.pics.mkConn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT pathThumbnail, pathPreview FROM assets WHERE autoId = ?", [aid])
                    row = cursor.fetchone()

                    if row:
                        if photoQ == ks.db.preview: return row[1]
                        return row[0]
                    return None

            result = getCache(cache_key, query_image, 'image/jpeg')
            if result: return result

            return send_file(pathNoImg, mimetype='image/png')

        except Exception as e:
            lg.error(f"Error serving image: {str(e)}")
            return send_file(pathNoImg, mimetype='image/png')

    #----------------------------------------------------------------
    # serve for LivePhoto Video
    #----------------------------------------------------------------
    @app.server.route('/api/livephoto/<aid>')
    def doGetLivePhotoBy(aid):
        try:
            cache_key = f"lp_{aid}"

            def query_livephoto():
                with db.pics.mkConn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT pathVdo FROM assets WHERE autoId = ?", [aid])
                    row = cursor.fetchone()

                    if not row or not row[0]:
                        lg.warn(f"[serve] no livePhoto aid[{aid}] path[ {row} ]")

                    return row[0] if row and row[0] else None

            result = getCache(cache_key, query_livephoto, 'video/quicktime')
            if result: return result

            return "", 404

        except Exception as e:
            lg.error(f"Error serving livephoto: {str(e)}")
            return "", 500

    #----------------------------------------------------------------
    # WebSocket URL endpoint
    #----------------------------------------------------------------
    @app.server.route('/api/conf')
    def getConf():
        try:
            import conf
            envs = conf.getEnvs()
            return jsonify(envs)
        except Exception as e:
            lg.error(f"[api] getConf Failed: {str(e)}")
            return jsonify({"error": f"Failed to get Conf, {str(e)}"}), 500

    #----------------------------------------------------------------
    # WebSocket Config endpoint
    #----------------------------------------------------------------
    @app.server.route('/api/ws-config')
    def getWsConfig():
        try:
            import conf
            wsConfig = conf.getWsConfig()
            return jsonify(wsConfig)
        except Exception as e:
            lg.error(f"[api] getWsConfig Failed: {str(e)}")
            return jsonify({"error": f"Failed to get WsConfig, {str(e)}"}), 500

    #----------------------------------------------------------------
    # System Check endpoint
    #----------------------------------------------------------------
    @app.server.route('/api/chk')
    def getChkResults():
        try:
            import chk
            chks = chk.checkSystem()
            return jsonify(chks)
        except Exception as e:
            lg.error(f"[api] getChkResults Failed: {str(e)}")
            return jsonify({"error": f"Failed to get ChkResults, {str(e)}"}), 500
