from typing import Any
from dsh import htm, dcc

from db import dto
from util import log
from mod import models
from conf import ks

lg = log.get(__name__)


def render():
    items: list[Any] = []

    def mk(kid, dta):
        sto = dcc.Store(
            id=kid,
            storage_type='session',  # memory, local, session
            data=dta
        )
        items.append(sto)

    lg.info("---------------------------------------")
    lg.info("[session] Initializing..")

    now: models.Now = models.Now()
    nfy: models.Nfy = models.Nfy()
    tsk: models.Tsk = models.Tsk()
    mdl: models.Mdl = models.Mdl()
    cnt: models.Cnt = models.Cnt()
    ste: models.Ste = models.Ste()
    sys: models.Sys = models.Sys()

    cnt.refreshFromDB()


    photoQ = dto.photoQ
    if not photoQ or photoQ not in [ ks.db.thumbnail, ks.db.preview ]:
        dto.photoQ = ks.db.thumbnail

    from conf import co
    dto.thMin = co.vad.float(dto.thMin, 0.93, mi=0.50, mx=0.99)



    mk(ks.sto.now, now.toDict())
    mk(ks.sto.nfy, nfy.toDict())
    mk(ks.sto.tsk, tsk.toDict())
    mk(ks.sto.mdl, mdl.toDict())
    mk(ks.sto.cnt, cnt.toDict())
    mk(ks.sto.ste, ste.toDict())
    mk(ks.sto.sys, sys.toDict())


    items.append(htm.Div(id=ks.sto.init, children='init'))

    return htm.Div(items, style={'display': 'none'})
