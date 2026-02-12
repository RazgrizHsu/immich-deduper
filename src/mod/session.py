from typing import Any
from dsh import htm, dcc

from db import dto
from mod.models.base import BaseDictModel
from util import log
from mod import models
from conf import ks

lg = log.get(__name__)


def render():
	items: list[Any] = []

	def mk(kid, dta):
		if isinstance(dta, BaseDictModel): dta = dta.toDict()
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
	sets: models.Sets = models.Sets()
	sets.ausl = dto.ausl.raw() #type: ignore

	cnt.refreshFromDB()


	photoQ = dto.photoQ
	if not photoQ or photoQ not in [ks.db.thumbnail, ks.db.preview]: dto.photoQ = ks.db.thumbnail

	from conf import co
	dto.thMin = co.vad.float(dto.thMin, 0.93, mi=0.50, mx=1.0)


	mk(ks.sto.pgSim, models.PgSim())

	mk(ks.sto.now, now)
	mk(ks.sto.nfy, nfy)
	mk(ks.sto.tsk, tsk)
	mk(ks.sto.mdl, mdl)
	mk(ks.sto.cnt, cnt)
	mk(ks.sto.ste, ste)
	mk(ks.sto.sys, sys)
	mk(ks.sto.sets, sets)


	items.append(htm.Div(id=ks.sto.init, children='init'))

	return htm.Div(items, style={'display': 'none'})
