import threading
import time
from datetime import datetime
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set

from flask_socketio import SocketIO, emit
from flask import request

from util import log

lg = log.get(__name__)

from mod.models import TskStatus, IFnRst, IFnProg, Gws

DEBUG = False


@dataclass
class TskInfo:
    sn: str
    name: str
    dtc: float
    status: TskStatus = TskStatus.PENDING
    prog: int = 0
    msg: str = ""
    result: Optional[IFnRst] = None
    err: Optional[str] = None
    dts: Optional[float] = None
    dte: Optional[float] = None

    def gws(self, typ:str):
        ti = self
        g = Gws.mk( typ, ti.sn, ti.status.value, ti.name, ti.msg, ti.prog )
        return g


@dataclass
class BseTsk(ABC):
    name: str = field()

    @abstractmethod
    def run(self, doReport: Optional[IFnProg] = None) -> Any:
        pass


#========================================================================
# Task Manager
#========================================================================
class TskMgr:
    def __init__(self):
        self.socketio: Optional[SocketIO] = None
        self.infos: Dict[str, TskInfo] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.tsks: Dict[str, BseTsk] = {}
        self.connected_clients: Set[str] = set()
        self.running = False

    def _sendCurrentTaskStatus(self, client_id: str):
        try:
            tsks = [(tsn, ti) for tsn, ti in self.infos.items() if ti.status in [TskStatus.RUNNING, TskStatus.PENDING]]

            if not tsks: return

            for tsn, ti in tsks:
                lg.info(f"[tskMgr] Sending current task status to new client: {ti.name} - {ti.status.value}")

                if self.socketio:
                    self.socketio.emit('task_message', ti.gws('start').toDict(), room=client_id)

                    if ti.status == TskStatus.RUNNING:
                        msg = ti.gws('prog')
                        self.socketio.emit('task_message', msg.toDict(), room=client_id)

                break  # Only one task should be running at a time
        except Exception as e:
            lg.error(f"[tskMgr] Error sending current task status: {e}")

    def setup_socketio(self, socketio: SocketIO):
        self.socketio = socketio
        self._register_handlers()
        lg.info(f"[tskMgr] SocketIO setup completed")

    def _register_handlers(self):
        if not self.socketio: return
        
        self.socketio.on_event('connect', self._handle_connect)
        self.socketio.on_event('disconnect', self._handle_disconnect) 
        self.socketio.on_event('message', self._handle_message)

    def _handle_connect(self):
        client_id = request.sid
        self.connected_clients.add(client_id)
        
        cnt = len(self.connected_clients)
        lg.info(f"[tskMgr] connected.. Total[{cnt}] client[{client_id}]")
        
        # Send connected message
        emit('task_message', Gws.mk('connected', '', '', '', '', 0).toDict())
        
        # Send current running task status to newly connected client
        self._sendCurrentTaskStatus(client_id)

    def _handle_disconnect(self):
        client_id = request.sid
        if client_id in self.connected_clients:
            self.connected_clients.remove(client_id)
            lg.info(f"[tskMgr] disconnected.. Total[{len(self.connected_clients)}] client[{client_id}]")

    def _handle_message(self, data):
        client_id = request.sid
        if DEBUG: lg.info(f"[tskMgr] Received message from client {client_id}: {data}")

    def broadcast(self, gws: Gws):
        if not self.socketio:
            lg.warning(f"[tskMgr] SocketIO not initialized, cannot broadcast {gws.typ}")
            return

        if self.connected_clients:
            try:
                # 廣播給所有連接的客戶端
                self.socketio.emit('task_message', gws.toDict())
                
                if gws.typ == 'progress':
                    if DEBUG: lg.info(f"[tskMgr] Progress sent: {gws.prg}%")
                elif gws.typ == 'complete':
                    lg.info(f"[tskMgr] Complete sent: status[{gws.ste}]")
                elif gws.typ == 'start':
                    lg.info(f"[tskMgr] Start sent: name[{gws.nam}]")
                    
                if DEBUG: lg.info(f"[tskMgr:broadcast] Sent to {len(self.connected_clients)} clients")
                
            except Exception as e:
                lg.error(f"[tskMgr] Broadcast error: {e}")

        elif gws.typ in ['start', 'progress', 'complete']:
            lg.warning(f"[tskMgr] No clients for [{gws.typ}] message")

    def start(self):
        if not self.running:
            self.running = True
            lg.info(f"[tskMgr] Task manager started")

    def stop(self):
        self.running = False

    def regBy(self, task: BseTsk) -> str:
        dt = datetime.now()
        sn = str(uuid.uuid4())

        ti = TskInfo(sn=sn, name=task.name, dtc=dt.timestamp())

        self.infos[sn] = ti
        self.tsks[sn] = task
        return sn

    def cancel(self, tsn: str) -> bool:
        if tsn not in self.infos: return False

        ti = self.infos[tsn]
        if ti.status in [TskStatus.COMPLETED, TskStatus.FAILED, TskStatus.CANCELLED]: return False

        ti.status = TskStatus.CANCELLED
        ti.dte = time.time()

        lg.info(f"[tskMgr] Task {tsn} cancelled, sending complete message")

        # Send cancel complete message to update UI
        if self.socketio:
            self.broadcast(ti.gws('complete'))

        return True

    def isCancelled(self, tsn: str) -> bool:
        if tsn not in self.infos: return False
        return self.infos[tsn].status == TskStatus.CANCELLED

    #------------------------------------------------
    # run on Thread
    #------------------------------------------------
    def _execOnThread(self, tsn: str):
        tk = self.tsks.get(tsn)
        ti = self.infos.get(tsn)

        if not tk or not ti: return

        ti.status = TskStatus.RUNNING
        ti.dts = time.time()

        #------------------------------------
        # sending
        #------------------------------------
        def doSend(gws:Gws):
            self.broadcast(gws)

        #------------------------------------
        dtu = 0

        def fnReport(pct: int, msg: str):
            if ti.status == TskStatus.CANCELLED: return  # Stop reporting if cancelled

            ti.prog = pct
            ti.msg = msg

            nonlocal dtu
            now = time.time()
            if now - dtu < 0.3 and pct < 100: return #limit sec
            dtu = now

            doSend(ti.gws('progress'))
            pass

        #------------------------------------
        try:
            doSend(ti.gws('start'))

            if ti.status != TskStatus.CANCELLED:
                sto, retMsg = tk.run(fnReport)

                if ti.status == TskStatus.CANCELLED:
                    ti.msg = "Task was cancelled"
                    ti.prog = 0
                else:
                    ti.status = TskStatus.COMPLETED
                    ti.result = sto
                    ti.prog = 100
                    ti.msg = retMsg

        except Exception as e:
            if ti.status == TskStatus.CANCELLED:
                ti.msg = "Task was cancelled"
            else:
                ti.status = TskStatus.FAILED
                ti.err = str(e)
                ti.msg = f"Error: {str(e)}"

        finally:
            ti.dte = time.time()

            # Only send complete message if not already sent by cancel()
            if ti.status != TskStatus.CANCELLED: doSend(ti.gws('complete') )

            if tsn in self.threads: del self.threads[tsn]

    def run(self, tsn: str) -> bool:
        if tsn not in self.infos:
            raise RuntimeError(f"Task {tsn} not found in tasks")

        if tsn in self.threads:
            raise RuntimeError(f"Task {tsn} already running")

        thread = threading.Thread(
            target=self._execOnThread,
            args=(tsn,),
            daemon=True
        )
        self.threads[tsn] = thread
        thread.start()
        # if DEBUG: lg.info(f"Task {tsn} thread started")
        return True


    def getInfo(self, tsn: str) -> Optional[TskInfo]:
        return self.infos.get(tsn)

    def list(self) -> Dict[str, TskInfo]:
        return self.infos.copy()


    def hasRunning(self):
        for tid, info in self.list().items():
            if info.status.value in ['pending', 'running']:
                return True

        return False
