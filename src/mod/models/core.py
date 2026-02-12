import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from enum import Enum

from .base import BaseDictModel


#------------------------------------------------------------------------
# types
#------------------------------------------------------------------------
IFnProg = Callable[[int, str], None]
IFnCancel = Callable[[], bool]


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
    msg: Union[str, List[str], None] = None
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

