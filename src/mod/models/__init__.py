import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union


from .base import BaseDictModel, Json
from .core import IFnProg, IFnCancel, TskStatus, Gws
from .mods import Pager, Nfy, Tsk, Mdl, MdlImg, ProcessInfo
from .shared import Sys, Cnt, Ste, Sets
from .data import SimInfo, Usr, Asset, AssetExif, AssetExInfo
from .data import Album, AssetFace, Tags, Library
from .page import PgSim, Now

#------------------------------------------------------------------------
# types
#------------------------------------------------------------------------
IFnRst = Tuple['ITaskStore', Optional[str | List[str]]]
IFnCall = Callable[[IFnProg, 'ITaskStore'], IFnRst]


#------------------------------------------------------------------------
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

