from dsh import htm, dbc, inp, out, ste, cbk, noUpd, getTrgId
from util import log
from mod import models
from conf import ks

lg = log.get(__name__)

class k:
	modal = 'modal-container'
	btnOk = 'modal-btn-ok'
	btnNo = 'modal-btn-no'
	body = 'modal-body'

def render():
	return dbc.Modal([
		dbc.ModalHeader("Confirm"),
		dbc.ModalBody(htm.Div(id=k.body)),
		dbc.ModalFooter([
			dbc.Button("Cancel", id=k.btnNo, className="ms-auto"),
			dbc.Button("Confirm", id=k.btnOk, color="danger"),
		]),
	], id=k.modal, is_open=False, centered=True),


#========================================================================
@cbk(
	[
		out(k.modal, "is_open", allow_duplicate=True),
		out(k.body, "children"),
		out(ks.sto.mdl, "data", allow_duplicate=True),
		out(ks.sto.nfy, "data", allow_duplicate=True),
	],
	inp(ks.sto.mdl, "data"),
	ste(ks.sto.nfy, "data"),
	ste(ks.glo.gws, "data"),
	prevent_initial_call=True
)
def mdl_Status(dta_mdl, dta_nfy, gws):
	nfy = models.Nfy.fromDic(dta_nfy)
	wms = models.Gws.fromDic(gws)
	if not wms.dtc:
		nfy.warn(f"WebSocket not connected, please check your config, wms: {wms}")
		return noUpd.by(4).upd(3, nfy)


	mdl = models.Mdl.fromDic(dta_mdl)
	isOpen = mdl.id is not None

	# lg.info(f"[modal] Trigger[{trigId}] mdl: id[{mdl.id}]")

	return isOpen, mdl.msg, mdl.toDict(), nfy.toDict()


#------------------------------------------------------------------------
# onclick
#------------------------------------------------------------------------
@cbk(
	[
		out(k.modal, "is_open", allow_duplicate=True),
		out(ks.sto.mdl, "data", allow_duplicate=True),
		out(ks.sto.tsk, "data", allow_duplicate=True),
		out(ks.sto.nfy, "data", allow_duplicate=True),
	],
	[
		inp(k.btnOk, "n_clicks"),
		inp(k.btnNo, "n_clicks"),
	],
	ste(ks.sto.mdl, "data"),
	ste(ks.sto.nfy, "data"),
	prevent_initial_call=True
)
def mdl_OnClick(nclk_ok, nclk_no, dta_mdl, dta_nfy):
	if not nclk_ok and not nclk_no: return noUpd.by(4)

	nfy = models.Nfy.fromDic(dta_nfy)
	mdl = models.Mdl.fromDic(dta_mdl)
	tsk = models.Tsk()

	trigId = getTrgId()

	# lg.info( f"[modal] Trigger[{trigId}] mdl: id[{mdl.id}]" )

	if trigId == k.btnNo:
		lg.info(f"[modal] Cancel execution: id[{mdl.id}]")
		mdl.reset()

	if trigId == k.btnOk:
		lg.info(f"[modal] Confirm execution: id[{mdl.id}] cmd[{mdl.cmd}]")
		mdl.ok = True

		if mdl.cmd:
			try:
				tsk = mdl.mkTsk()
				if not tsk:
					lg.error(f"[modal] Failed to create task from modal")
					tsk = models.Tsk()
				else: lg.info(f"[modal] Created task: id[{tsk.id}] cmd[{tsk.cmd}]")
			except Exception as e: lg.error(f'[mdl] create failed, {str(e)}, mdl[{mdl}]')
		else: lg.warn(f'[mdl] non cmd: {mdl}')

		mdl.reset()

	return False, mdl.toDict(), tsk.toDict(), nfy.toDict()
