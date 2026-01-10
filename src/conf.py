import os
import time
import random
import re
from typing import Dict, Callable, Optional

import dotenv
import torch

# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context

dotenv.load_dotenv()

from util import log

lg = log.get(__name__)


def getDevice():
    useDevice = os.getenv('ForceCpu')
    if useDevice: return torch.device('cpu')

    if torch.cuda.is_available():
        return torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    else:
        return torch.device('cpu')

device = getDevice()
pathRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
isDock = os.path.exists('/.dockerenv')


#------------------------------------------------------------------------
# code helper
#------------------------------------------------------------------------
class co:
    class to:
        @classmethod
        def dict(cls):
            return {key: value for key, value in vars(cls).items() if not key.startswith('_') and not callable(value)}


    @staticmethod
    def timeId():
        timestamp_ms = int(time.time() * 1000)
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        base36_timestamp = ""
        num = timestamp_ms
        while num > 0:
            base36_timestamp = alphabet[num % 36] + base36_timestamp
            num //= 36
        if not base36_timestamp: base36_timestamp = "0"

        random_part = ''.join(random.choices(alphabet, k=5))

        return base36_timestamp + random_part

    class tit(str):
        name: str = ''
        desc: str = ''
        cmds: Dict[str, 'co.tit'] = {}

        def __new__(cls, v='', name='', cmds: Optional[Dict[str, 'co.tit']] = None, desc='') -> 'co.tit':
            me = super().__new__(cls, v)
            me.name = name
            me.cmds = cmds if cmds else {}
            me.desc = desc
            # noinspection PyTypeChecker
            return me

    class find:
        @classmethod
        def find(cls, key: Optional[str]) -> 'Optional[co.tit]':
            for attr_name in dir(cls):
                if attr_name.startswith('__') or callable(getattr(cls, attr_name)): continue
                attr = getattr(cls, attr_name)
                if isinstance(attr, co.tit) and attr == key: return attr
            return None

        @classmethod
        def findBy(cls, key: str, value):
            for name in dir(cls):
                if name.startswith('__') or callable(getattr(cls, name)): continue
                obj = getattr(cls, name)
                if isinstance(obj, co.tit) and hasattr(obj, key):
                    if getattr(obj, key) == value: return obj
            return None

    class vad:
        @staticmethod
        def float(v, default, mi=0.01, mx=1.0):
            try:
                fv = float(v)
                if fv < mi or fv > mx: return default
                return fv
            except (ValueError, TypeError):
                return default
    class fmt:
        @staticmethod
        def date(v):
            rst = str(v)
            if isinstance(rst, str) and 'T' in rst and '+' in rst:
                ps = rst.split('T')
                if len(ps) == 2 and '+' in ps[1]:
                    tz = ps[1]
                    if '.' in tz and ('+' in tz or '-' in tz):
                        ptm = tz.split('.')
                        if len(ptm) == 2:
                            base_time = ptm[0]
                            tz_part = ptm[1].split('+')[-1] if '+' in ptm[1] else ptm[1].split('-')[-1]
                            sign = '+' if '+' in ptm[1] else '-'
                            tz = f"{base_time}{sign}{tz_part}"
                    rst = f"{ps[0]} {tz}"
            return rst

        @staticmethod
        def size(value):
            if isinstance(value, (int, float)):
                if value > 1024 * 1024:
                    return f"{value / (1024 * 1024):.2f} MB"
                elif value > 1024:
                    return f"{value / 1024:.2f} KB"
                else:
                    return f"{value} B"
            return value

#------------------------------------------------------------------------
# keys
#------------------------------------------------------------------------
class cmds:
    class fetch(co.to):
        asset = co.tit('fetch_asset',desc='Fetch assets from remote')
        clear = co.tit('fetch_clear',desc='Clear select user assets and vectors')
        reset = co.tit('fetch_reset',desc='Clear all assets and vectors')

    class vec(co.to):
        toVec = co.tit('vec_toVec',desc='Generate vectors from assets')
        clear = co.tit('vec_clear',desc='Clear all vectors')

    class sim(co.to):
        fnd = co.tit('sim_find', desc='Find Similar vectors')
        clear = co.tit('sim_clear', desc='Clear Similar results but keep simOk')
        reset = co.tit('sim_clearAll', desc='Clear all similar results')
        selOk = co.tit('sim_selOk', desc='Reslove selected assets')
        selRm = co.tit('sim_selRm', desc='Delete selected assets')
        allOk = co.tit('sim_allOk', desc='Reslove All assets')
        allRm = co.tit('sim_allRm', desc='Delete All assets')
    class view(co.to):
        assDel = co.tit('view_AssDel',desc='Delete asset')

class ks:
    title = "Immich-Deduper"
    cmd = cmds

    class glo:
        gws = 'global-ws'

    class pg(co.find):
        fetch = co.tit('fetch', 'Fetch', cmds.fetch.dict(), desc='Get photo asset from Immich')
        vector = co.tit('vector', 'Vectors', cmds.vec.dict(), desc='Process to generate vectors for similarity calculations')
        similar = co.tit('similar', 'Similar', cmds.sim.dict(), desc='Find similar photos based on settings')
        view = co.tit('view', 'View', cmds.view.dict(), desc='Use the filters and sorting options to customize your view')
        setting = co.tit('settings', 'Settings', desc='system settings')


    class db:
        thumbnail = 'thumbnail'
        preview = 'preview'

        class status:
            trashed = 'trashed'
            active = 'active'
            deleted = 'deleted'

    class use:
        api = 'API'
        dir = 'DIR'

        class mth:
            cosine = co.tit('cosine', 'Cosine Similarity')
            euclid = co.tit('euclidean', 'Euclidean Distance')


    class sto:
        init = 'store-init'
        now = 'store-now'
        tsk = 'store-tsk'
        nfy = 'store-nfy'
        mdl = 'store-mdl'
        mdlImg = 'store-mdl-img'

        cnt = 'store-count'
        ste = 'store-state'
        sys = 'store-sys'

        pgSim = 'sto-pg-sim'

    class defs:
        exif = {
            "exifImageWidth": "Width",
            "exifImageHeight": "Height",
            "fileSizeInByte": "File Size",
            "dateTimeOriginal": "Capture Time",
            "modifyDate": "Modify Time",
            "make": "Camera Brand",
            "model": "Camera Model",
            "lensModel": "Lens",
            "fNumber": "Aperture",
            "focalLength": "Focal Length",
            "exposureTime": "Exposure Time",
            "iso": "ISO",
            "orientation": "Orientation",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "city": "City",
            "state": "State",
            "country": "Country",
            "description": "Description",
            "fps": "Frame Rate",
            "livePhotoCID": "Live Photo CID",
            "timeZone": "Time Zone",
            "projectionType": "Projection Type",
            "profileDescription": "Profile Description",
            "colorspace": "Color Space",
            "bitsPerSample": "Bits Per Sample",
            "autoStackId": "Auto Stack ID",
            "rating": "Rating",
            # "updatedAt": "Updated At",
            # "updateId": "Update ID"
        }

    class css:
        show = {"display": ""}
        hide = {"display": "none"}


#------------------------------------------------------------------------
# helpers
#------------------------------------------------------------------------
class url:
    @staticmethod
    def get_image_url(assetId, photoQ=ks.db.thumbnail):
        return f"/api/image/{assetId}?quality={photoQ}"

def pathFromRoot(path):
    if os.path.isabs(path): return path
    joined_path = os.path.join(pathRoot, path)
    return os.path.normpath(joined_path)

#------------------------------------------------------------------------
# envs
#------------------------------------------------------------------------
class envs:
    version='0.1.13'
    isDev = False if isDock else bool(os.getenv('IsDev', False))
    isDevUI = False if isDock else bool(os.getenv('IsDevUI', False))
    isDock = False if not isDock else True
    immichPath:str = '/immich' if isDock else os.getenv('IMMICH_PATH', '')
    immichThumb:str = os.getenv('IMMICH_THUMB', '')
    qdrantUrl:str = 'http://immich-deduper-qdrant:6333' if isDock else os.getenv('QDRANT_URL','')
    psqlHost:str = os.getenv('PSQL_HOST','')
    psqlPort:str = os.getenv('PSQL_PORT','')
    psqlDb:str = os.getenv('PSQL_DB','')
    psqlUser:str = os.getenv('PSQL_USER','')
    psqlPass:str = os.getenv('PSQL_PASS','')
    mkitPort:str = os.getenv('DEDUP_PORT', '8086')

    if os.getcwd().startswith(os.path.join(pathRoot, 'tests')):
        mkitData = os.path.join(pathRoot, 'data/')
    else:
        mkitData = 'data/' if isDock else os.getenv('DEDUP_DATA', os.path.join(pathRoot, 'data/'))
        if not mkitData.endswith('/'): mkitData += '/'

    class pth:
        @staticmethod
        def base(path: Optional[str]) -> str:
            if not path: return ""

            mth = re.match(r'^(?:.*/)?(?:thumbs|encoded-video)/(.+)$', path)
            if mth: return mth.group(1)
            return ""

        @staticmethod
        def normalize(path: Optional[str]) -> str:
            if not path: return ""

            basePath = envs.pth.base(path)
            if basePath:
                if '/thumbs/' in path or path.startswith('thumbs/'):
                    return f"thumbs/{basePath}"
                elif '/encoded-video/' in path or path.startswith('encoded-video/'):
                    return f"encoded-video/{basePath}"

            return path

        @staticmethod
        def full(path: Optional[str]) -> str:
            if not path: return ""

            nor = envs.pth.normalize(path)
            if not nor: return ""

            if os.path.isabs(nor): return nor

            if envs.immichThumb and nor.startswith('thumbs/'):
                fullPath = os.path.join(envs.immichThumb, nor.replace('thumbs/', ''))
                return os.path.normpath(fullPath)

            if nor.startswith(envs.immichPath): return nor

            fullPath = os.path.join(envs.immichPath, nor)
            return os.path.normpath(fullPath)

        @staticmethod
        def forImg(pathThumb: Optional[str], pathPreview: Optional[str] = None, photoQ: Optional[str] = None) -> str:
            if photoQ == ks.db.preview and pathPreview:
                return envs.pth.full(pathPreview)
            if pathThumb:
                return envs.pth.full(pathThumb)
            if pathPreview:
                return envs.pth.full(pathPreview)
            return ""

    @staticmethod
    def showVars():
        def maskSensitive(value: str, keepStart: int = 2, keepEnd: int = 1) -> str:
            if not value or len(value) <= keepStart + keepEnd:
                return '*' * len(value) if value else ''
            return value[:keepStart] + '*' * (len(value) - keepStart - keepEnd) + value[-keepEnd:]

        lg.info("Environment variables loaded:")
        lg.info(f"  PSQL_HOST: {envs.psqlHost}")
        lg.info(f"  PSQL_PORT: {envs.psqlPort}")
        lg.info(f"  PSQL_DB: {envs.psqlDb}")
        lg.info(f"  PSQL_USER: {envs.psqlUser}")
        lg.info(f"  PSQL_PASS: {maskSensitive(envs.psqlPass)}")
        lg.info(f"  IMMICH_PATH: {envs.immichPath}")
        lg.info(f"  IMMICH_THUMB: {envs.immichThumb}")
        lg.info(f"  QDRANT_URL: {envs.qdrantUrl}")
        lg.info(f"  DEDUP_PORT: {envs.mkitPort}")
        lg.info(f"  DEDUP_DATA: {envs.mkitData}")
        lg.info(f"  IS_DOCKER: {envs.isDock}")
        lg.info(f"  IS_DEV: {envs.isDev}")

#------------------------------------------------------------------------
#------------------------------------------------------------------------
def getHostName():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return None

def getEnvs():
    return { 'port':envs.mkitPort }

def getWsConfig():
    return {
        'isDevUI': envs.isDevUI
    }

#------------------------------------------------------------------------
# const
#------------------------------------------------------------------------

pathCache = envs.mkitData + 'cache/'
