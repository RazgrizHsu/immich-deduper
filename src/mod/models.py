import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union

from dsh import htm
from conf import ks, envs, co
from util import log
from .bse.baseModel import BaseDictModel

lg = log.get(__name__)

#------------------------------------------------------------------------
# types
#------------------------------------------------------------------------
IFnProg = Callable[[int, str], None]
IFnCancel = Callable[[], bool]
IFnRst = Tuple['ITaskStore', Optional[str | List[str]]]
IFnCall = Callable[[IFnProg, 'ITaskStore'], IFnRst]


#------------------------------------------------------------------------
@dataclass
class Nfy(BaseDictModel):
    msgs: List[Dict[str, Any]] = field(default_factory=list)

    def _init__(self, msgs): self.msgs = msgs

    def info(self, msg: Union[str, List[str]], to=5000):
        lg.info(f"[notify] {msg}")
        self._add(self._format_message(msg), "info", to)

    def success(self, msg: Union[str, List[str]], to=5000):
        lg.info(f"[notify] {msg}")
        self._add(self._format_message(msg), "success", to)

    def warn(self, msg: Union[str, List[str]], to=8000):
        lg.warning(f"[notify] {msg}")
        self._add(self._format_message(msg), "warning", to)

    def error(self, msg: Union[str, List[str]], to=0):
        lg.error(f"[notify] {msg}")
        self._add(self._format_message(msg), "danger", to)

    def _format_message(self, msg: Union[str, List[str]]):
        if isinstance(msg, str):
            if '\n' in msg:
                parts = msg.split('\n')
                rst = []
                for i, part in enumerate(parts):
                    if i > 0: rst.append(htm.Br())
                    rst.append(part)
                return rst
            return msg
        elif isinstance(msg, list):
            rst = []
            for i, item in enumerate(msg):
                if i > 0: rst.append(htm.Br())
                rst.append(item)
            return rst
        return msg

    def _add(self, msg, typ, to):
        nid = time.time()
        self.msgs.append({'id': nid, 'message': msg, 'type': typ, 'timeout': to})

    def remove(self, nid):
        self.msgs = [msg for msg in self.msgs if msg.get('id') != nid]


@dataclass
class Cmd(BaseDictModel):
    id: Optional[str] = None
    cmd: Optional[co.tit] = None
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tsk(Cmd):
    tsn: Optional[str] = None
    name: Optional[str] = None
    msg: Optional[str] = None

    nexts: List['Tsk'] = field(default_factory=list)

    def reset(self):
        self.id = self.name = self.cmd = self.msg = None
        self.args = {}

        self.tsn = None
    def clear(self):
        self.id = self.cmd = None


@dataclass
class Mdl(Cmd):
    msg: Optional[str | List[Any]] = None
    ok: bool = False

    assets: List['Asset'] = field(default_factory=list)

    def reset(self):
        self.id = self.msg = self.cmd = None
        self.ok = False
        self.args = {}
        self.assets = []

    def mkTsk(self):
        tsk = Tsk()

        tit = ks.pg.find(self.id)
        if not tit: raise RuntimeError(f"not found tit for id[{self.id}]")

        # lg.info( f"tit.cmds({type(tit.cmds)}) => {tit.cmds}" )
        if not self.cmd in tit.cmds.values(): raise RuntimeError(f'the MDL.cmd[{self.cmd}] not in [{tit.cmds}]')

        cmd = next(v for k, v in tit.cmds.items() if v == self.cmd)
        # lg.info( f"cmd => type({type(cmd)}) v:{cmd}" )

        tsk.id = self.id
        tsk.name = tit.name
        tsk.cmd = self.cmd
        tsk.args |= self.args

        if hasattr(cmd, 'desc'): tsk.msg = cmd.desc

        return tsk

@dataclass
class MdlImg(BaseDictModel):
    open: bool = False
    imgUrl: Optional[str] = None
    isMulti: bool = False
    curIdx: int = 0
    helpCollapsed: bool = False
    infoCollapsed: bool = False


@dataclass
class Tab(BaseDictModel):
    title: Optional[str] = None
    disabled: Optional[bool] = False
    active: bool = False
    rehit: bool = False  # 是否允許重複點擊刷新
    id: Optional[str] = None  # 可選，如果不提供會自動生成
    idx: Optional[int] = None  # 內部使用，記錄 tab 的索引

    def css(self):
        css = ""
        if self.active: css += " act"
        if self.disabled: css += " dis"
        return css.strip()



@dataclass
class Pager(BaseDictModel):
    idx: int = 1
    size: int = 20
    cnt: int = 0


@dataclass
class ProcessInfo(BaseDictModel):
    all: int = 0
    skip: int = 0
    erro: int = 0
    done: int = 0


@dataclass
class SimInfo(BaseDictModel):
    aid: int = 0
    score: float = 0
    isSelf: bool = False


@dataclass
class Usr(BaseDictModel):
    id: str = ''
    name: str = ''
    email: str = ''


@dataclass
class AssetExif(BaseDictModel):
    make: Optional[str] = None
    model: Optional[str] = None
    exifImageWidth: Optional[int] = None
    exifImageHeight: Optional[int] = None
    fileSizeInByte: Optional[int] = None
    orientation: Optional[str] = None
    dateTimeOriginal: Optional[str] = None
    modifyDate: Optional[str] = None
    lensModel: Optional[str] = None
    fNumber: Optional[float] = None
    focalLength: Optional[float] = None
    iso: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    fps: Optional[float] = None
    exposureTime: Optional[str] = None
    livePhotoCID: Optional[str] = None
    timeZone: Optional[str] = None
    projectionType: Optional[str] = None
    profileDescription: Optional[str] = None
    colorspace: Optional[str] = None
    bitsPerSample: Optional[int] = None
    autoStackId: Optional[str] = None
    rating: Optional[int] = None
    updatedAt: Optional[str] = None
    updateId: Optional[str] = None

    def toAvDict(self):
        return {k: v for k, v in self.toDict().items() if v is not None}


@dataclass
class AssetViewOnly(BaseDictModel):

    isMain:bool = False

    cntRelats: int = 0

    score: float = 0.0

    srcAutoId: int = 0
    isRelats: bool = False

    muodId: int = 0

@dataclass
class Asset(BaseDictModel):
    autoId: int = 0
    id: str = ""
    ownerId: Optional[str] = None
    deviceId: Optional[str] = None
    vdoId: Optional[str] = None
    type: Optional[str] = None
    originalFileName: Optional[str] = None
    fileCreatedAt: Optional[str] = None
    fileModifiedAt: Optional[str] = None
    isFavorite: Optional[int] = 0
    isVisible: Optional[int] = 0
    isArchived: Optional[int] = 0
    localDateTime: Optional[str] = None
    pathThumbnail: Optional[str] = None
    pathPreview: Optional[str] = None
    pathFullsize: Optional[str] = None
    pathVdo: Optional[str] = None
    jsonExif: AssetExif = field(default_factory=AssetExif)
    isVectored: Optional[int] = 0
    simOk: Optional[int] = 0
    simInfos: List[SimInfo] = field(default_factory=list)
    simGIDs: List[int] = field(default_factory=list)

    # view only
    view: AssetViewOnly = field(default_factory=AssetViewOnly)

    def getImagePath(self, photoQ=None):
        if photoQ == ks.db.fullsize:
            path = self.pathFullsize
        elif photoQ == ks.db.preview:
            path = self.pathPreview
        else:
            path = self.pathThumbnail

        if not path: path = self.pathThumbnail

        if not path: raise RuntimeError(f"the thumbnail path is empty, assetId[{self.id}]")

        return os.path.join(envs.immichPath, path)


@dataclass
class Album(BaseDictModel):
    id: str = ""
    ownerId: str = ""
    albumName: str = ""
    description: str = ""
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    albumThumbnailAssetId: Optional[str] = None
    isActivityEnabled: bool = True
    order: str = "asc"


@dataclass
class Cnt(BaseDictModel):
    ste: int = 0

    ass: int = 0  # 總資產數
    vec: int = 0  # 已向量化數
    simOk: int = 0
    simNo: int = 0
    simPnd: int = 0  # 待處理相似數

    def reset(self):
        self.ass = self.vec = self.simOk = self.simPnd = 0

    def refreshFromDB(self):
        import db
        self.ass = db.pics.count()
        self.vec = db.vecs.count()
        self.simOk = db.pics.countSimOk(1)
        self.simNo = db.pics.countSimOk(0)
        self.simPnd = db.pics.countSimPending();

    @classmethod
    def mkNewCnt(cls) -> 'Cnt':
        cnt = cls()
        cnt.refreshFromDB()
        return cnt


@dataclass
class Ste(BaseDictModel):
    cntTotal: int = 0
    selectedIds: List[int] = field(default_factory=list)

    def clear(self):
        self.selectedIds.clear()
        self.cntTotal = 0

    def getSelected(self, allAssets: List[Asset]) -> List[Asset]:
        return [a for a in allAssets if a.autoId in self.selectedIds]




@dataclass
class PgSim(BaseDictModel):
    pagerPnd: Optional[Pager] = None
    activeTab: Optional[str] = "tab-current"



    assAid: int = 0
    assCur: List[Asset] = field(default_factory=list)

    assPend: List[Asset] = field(default_factory=list)

    assFromUrl: Optional[Asset] = None

    fspSize: bool = False
    fspW: bool = False
    fspH: bool = False

    def clearNow(self):
        self.assAid = 0
        self.assFromUrl = None
        self.assCur.clear()

    def clearAll(self):
        self.clearNow()
        self.assPend.clear()

@dataclass
class Sets(BaseDictModel):
    photoQ: str = ks.db.thumbnail
    thMin: float = 0.93

    autoNext: bool = True
    showInfo: bool = True


@dataclass
class Now(BaseDictModel):
    sim: PgSim = field(default_factory=PgSim)

from enum import Enum

class TskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Gws(BaseDictModel):
    dtc: float = time.time()
    tsn: str = ''
    typ: Optional[str] = None
    nam: Optional[str] = None
    msg: Optional[str] = None
    ste: Optional[TskStatus] = None
    prg: float = 0.0


    @classmethod
    def mk(cls, typ, tsn=None, ste=None, nam=None, msg=None, prg=0.0):

        m = cls()
        if typ: m.typ = typ
        if tsn: m.tsn = tsn
        if ste: m.ste = ste
        if nam: m.nam = nam
        if msg: m.msg = msg
        if prg: m.prg = prg
        return m

    def jstr(self): return self.toJson()

    @classmethod
    def jsonStr(cls, typ, tsn=None, ste=None, nam=None, msg=None, prg=0.0):

        m = cls()
        if typ: m.typ = typ
        if tsn: m.tsn = tsn
        if ste: m.ste = ste
        if nam: m.nam = nam
        if msg: m.msg = msg
        if prg: m.prg = prg
        return m.toJson()


@dataclass
class ITaskStore:
    nfy: Nfy
    now: Now
    cnt: Cnt
    tsk: Tsk
    ste: Ste

    _canceller: Optional[IFnCancel] = None

    def isCancelled(self) -> bool:
        if self._canceller: return self._canceller()
        return False

    def setCancelChecker(self, checker: IFnCancel):
        self._canceller = checker
