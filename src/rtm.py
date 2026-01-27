import os
import re
from typing import Dict, Optional
from util import log
lg = log.get(__name__)

from dto import dto
from conf import envs, ks


immichPath: str
immichThumb: str
libPaths: Dict[str, str]
pathHostMap: Dict[str, str] = {}

_fieldMap = {
    'immichPath': 'pathImmich',
    'immichThumb': 'pathThumb',
}

def __getattr__(name: str):
    if name in _fieldMap: return getattr(dto, _fieldMap[name], '')
    if name == 'libPaths': return dto.pathLibs
    raise AttributeError(f"module 'rtm' has no attribute '{name}'")


def libPath(immichPath: str) -> str: return dto.pathLibs.get(immichPath, '')

def setLibPath(immichPath: str, localPath: str):
    mapping = dto.pathLibs.copy()
    mapping[immichPath] = localPath
    dto.pathLibs = mapping


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
        basePath = pth.base(path)
        if basePath:
            if '/thumbs/' in path or path.startswith('thumbs/'): return f"thumbs/{basePath}"
            elif '/encoded-video/' in path or path.startswith('encoded-video/'): return f"encoded-video/{basePath}"
        return path

    @staticmethod
    def full(path: Optional[str]) -> str:
        if not path: return ""

        nor = pth.normalize(path)
        if not nor: return ""

        # external library
        for immichPth, localPth in dto.pathLibs.items():
            if nor.startswith(immichPth) and localPth: return nor.replace(immichPth, localPth, 1)

        # /data → pathImmich
        if nor.startswith('/data/') and dto.pathImmich: return nor.replace('/data', dto.pathImmich, 1)

        # Docker mode: use verified host path mapping
        for hostPth, contPth in pathHostMap.items():
            hostPth = hostPth.rstrip('/')
            if nor.startswith(hostPth + '/') or nor == hostPth:
                return nor.replace(hostPth, contPth.rstrip('/'), 1)

        if os.path.isabs(nor): return nor

        if dto.pathThumb and nor.startswith('thumbs/'):
            fullPath = os.path.join(dto.pathThumb, nor.replace('thumbs/', ''))
            return os.path.normpath(fullPath)

        if nor.startswith(dto.pathImmich): return nor

        fullPath = os.path.join(dto.pathImmich, nor)
        return os.path.normpath(fullPath)

    @staticmethod
    def forImg(pathThumb: Optional[str], pathPreview: Optional[str]=None, photoQ: Optional[str]=None) -> str:
        if photoQ == ks.db.preview and pathPreview: return pth.full(pathPreview)
        if pathThumb: return pth.full(pathThumb)
        if pathPreview: return pth.full(pathPreview)
        return ""


# init
if len(dto.pathImmich) == 0 and envs.immichPath:
    if os.path.exists(envs.immichPath):
        lg.info(f'init immichPath from env[{envs.immichPath}]')
        dto.pathImmich = envs.immichPath
    else:
        lg.warn(f'init immichPath: path not found [{envs.immichPath}]')

if len(dto.pathThumb) == 0 and envs.immichThumb:
    if os.path.exists(envs.immichThumb):
        lg.info(f'init immichThumb from env[{envs.immichThumb}]')
        dto.pathThumb = envs.immichThumb
    else:
        lg.warn(f'init immichThumb: path not found [{envs.immichThumb}] - check volume mount')
