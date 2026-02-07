import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union

from dsh import htm
from conf import ks, envs, co
from util import log
from dtom import Ausl
from .core import IFnCancel
from .base import BaseDictModel
from .data import Asset
from .mods import Nfy, Tsk


lg = log.get(__name__)

@dataclass
class Sys(BaseDictModel):
    ok: bool = False


@dataclass
class Cnt(BaseDictModel):
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
    sysOk: bool = False

    def clear(self):
        self.selectedIds.clear()
        self.cntTotal = 0
        return self

    def getSelected(self, allAssets: List[Asset]) -> List[Asset]:
        return [a for a in allAssets if a.autoId in self.selectedIds]


@dataclass
class Sets(BaseDictModel):
    ausl: Ausl = field(default_factory=Ausl)

