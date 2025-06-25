from typing import Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from util import log
from flask_socketio import SocketIO

from mod.mgr.tskMgr import BseTsk, TskMgr
from mod.models import Tsk, ITaskStore, IFnProg

lg = log.get(__name__)

mgr: Optional[TskMgr] = None
socketio_instance: Optional[SocketIO] = None

@dataclass
class DashTask(BseTsk):
    tsk: Tsk
    fn: Callable
    store: ITaskStore

    # def __init__(self, tsk: models.Tsk, fn: Callable, store: ITaskStore):
    #     super().__init__(tsk.name)
    #     self.fn = fn
    #     self.store = store
    #     self.tsk = tsk

    @classmethod
    def mk(cls, tsk: Tsk, fn: Callable, store: ITaskStore):
        if not tsk: raise RuntimeError( "cannot create DashTask without tsk" )
        if not tsk.name: raise RuntimeError( f"cannot create DashTask by tsk[{tsk}]" )
        return cls(
            name=tsk.name,
            tsk=tsk,
            fn=fn,
            store=store
        )

    def run(self, doReport: Optional[IFnProg] = None) -> Any:

        #------------------------------------
        # adapter
        #------------------------------------
        def report(pct: int, msg: str):
            if doReport: doReport(pct, f"{msg}")
            # lg.info(f"[Task] id[{self.tskId}] progress: {percent}% - {label} - {msg}")

        #------------------------------------
        try:
            rst = self.fn(report, self.store)

            if len(rst) != 2:
                raise RuntimeError( f"[Task] name[{self.name}] fn shound returned 2values now[ {len(rst)} ]" )

            sto, msg = rst
            return sto if sto else self.store, msg

        except Exception as e:
            lg.error(f"[Task] name[{self.name}] call fn failed: {str(e)}")
            raise

def setup(socketio: SocketIO):
    global mgr, socketio_instance
    if not mgr:
        try:
            socketio_instance = socketio
            mgr = TskMgr()
            mgr.setup_socketio(socketio)
            lg.info(f"[tskSvc] Setup completed with SocketIO")
        except Exception as e:
            lg.error(f"[tskSvc] Setup Failed: {str(e)}")
            raise RuntimeError(f"[tskSvc] Setup failed: {str(e)}")

def stop():
    global mgr
    if mgr:
        mgr.stop()
        mgr = None
        lg.info("[tskSvc] Stopped")

def mkTask(tsk: Tsk, fn: Callable, sto: ITaskStore) -> str:
    if not mgr: raise RuntimeError("TskMgr not initialized")

    tskSn = mgr.regBy(DashTask.mk(tsk, fn, sto))

    # Inject cancel checker into store
    sto.setCancelChecker(lambda: mgr.isCancelled(tskSn)) #type:ignore

    return tskSn

def runBy(tskId: str) -> bool:
    if not mgr: raise RuntimeError("TskMgr not initialized")

    return mgr.run(tskId)

def cancelBy(tskId: str) -> bool:
    if not mgr: return False
    return mgr.cancel(tskId)


def getResultBy(tskId: str) -> ITaskStore:
    if not mgr: raise RuntimeError( "TskMgr not init" )

    ti = mgr.getInfo(tskId)
    if ti and tskId in mgr.tsks:
        dTsk = mgr.tsks[tskId]
        if isinstance(dTsk, DashTask): return dTsk.store

    raise RuntimeError(f"[TskSvc] failed get result from tskId[{tskId}]")
