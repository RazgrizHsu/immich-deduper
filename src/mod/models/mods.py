
import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union

from dsh import htm
from conf import ks, envs, co
from util import log
from .base import BaseDictModel

lg = log.get(__name__)




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
        nid = co.timeId()
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

    def reset(self):
        self.id = self.msg = self.cmd = None
        self.ok = False
        self.args = {}

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
    hideHelp: bool = False
    hideInfo: bool = False
    modeH: bool = False

