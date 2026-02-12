import db
from db import psql
import json
from conf import ks
from dsh import dash, htm, dcc, cbk, ccbk, cbkFn, dbc, inp, out, ste, getTrgId, noUpd, ALL
from mod import models
from mod.models import Pager
from ui import pager, gv
from util import log

lg = log.get(__name__)

dash.register_page(
	__name__,
	path=f'/{ks.pg.view}',
	title=f"{ks.title}: " + 'Assets Grid',
)

class k:
	selUsrId = "inp-grid-user-selector"
	selFilter = "inp-grid-filter"
	schKeyword = "inp-grid-search"
	schPath = "inp-grid-path"
	cbxFav = "inp-favorites"
	cbxArc = "inp-archived"
	cbxLive = "inp-livePhoto"
	cbxGridInfo = "inp-grid-info"

	btnExportIds = "view-btn-ExportIds"

	grid = "div-photo-grid"
	pagerMain = "vg-pager-main"

	initView = "view-init"


optFileters = [
	{"label": "All Assets", "value": "all"},
	{"label": "With Vectors", "value": "with_vectors"},
	{"label": "Without Vectors", "value": "without_vectors"}
]

#========================================================================
def layout():
	import ui

	# Get initial total for display
	try: total = db.pics.count()
	except: total = 0

	return ui.renderBody([
		#====== top start =======================================================

		htm.Div([
			htm.H3(f"{ks.pg.view.name}"),
			htm.Small(f"{ks.pg.view.desc}", className="text-muted")
		], className="body-header"),

		dbc.Card([
			dbc.CardHeader("View Settings"),
			dbc.CardBody([
				dbc.Row([
					dbc.Col([
						dbc.Label("User"),
						dbc.Select(id=k.selUsrId, options=[{"label": "All Users", "value": ""}], value="", className="mb-2"),
					], width=4),
					dbc.Col([
						dbc.Label("Filter"),
						dbc.Select(id=k.selFilter, options=optFileters, value="all", className="mb-2"), #type:ignore
					], width=4),
					dbc.Col([
						dbc.Label("Export"),
						dbc.Button("Export Current IDs", id=k.btnExportIds, color="info", className="w-100"),
					])
				]),

				dbc.Row([
					dbc.Col([
						dbc.Label("Filename"),
						dbc.Input(id=k.schKeyword, type="text", placeholder="Search by filename...", className="mb-2"),
					], width=4),
					dbc.Col([
						dbc.Label("Path Contains"),
						dbc.Input(id=k.schPath, type="text", placeholder="e.g. /store/user/folder", className="mb-2"),
					], width=4),
					dbc.Col([
						dbc.Checkbox(id=k.cbxFav, label="Favorites", value=False, className="mt-4"),
						dbc.Checkbox(id=k.cbxArc, label="Archived", value=False, className="mt-2"),
						dbc.Checkbox(id=k.cbxLive, label="LivePhoto", value=False, className="mt-2"),
						dbc.Checkbox(id=k.cbxGridInfo, label="Show Grid Info", value=db.dto.showGridInfo, className="mt-2"),
						htm.Div(id={"type": "dummy", "id": "grid-info-view"}, style={"display": "none"}),
					], width=4),
				]),

				dbc.Row([
					dbc.Col([
						htm.Ul([
							htm.Li(["Searching with 'Find similar #number' follows your Similar configurations"]),
						])
					], width=12),
				]),

				dbc.Row([
					dbc.Col([
					], width=2, className="ms-auto"),
				], className="mt-2"),
			])
		], className="mb-4"),
		#====== top end =========================================================
	], [
		#====== bottom start=====================================================

		htm.Div([
			# Top pager
			*pager.createPager(pgId=k.pagerMain, idx=0, className="mb-3 text-center", btnSize=9),

			# Grid
			dbc.Spinner(
				htm.Div(id=k.grid, className="mb-4"),
				color="primary",
				type="border",
				spinner_style={"width": "3rem", "height": "3rem"}
			),

			# Bottom pager
			*pager.createPager(pgId=k.pagerMain, idx=1, className="mt-3 text-center", btnSize=9),

			# Main pager store
			*pager.createStore(pgId=k.pagerMain, page=1, total=total)
		]),

		# Init store
		dcc.Store(id=k.initView),

		#====== bottom end ======================================================
	])

#========================================================================
# Register pager callbacks
#========================================================================
pager.regCallbacks(k.pagerMain)

#========================================================================
# Page initialization - initialize user options
#========================================================================
@cbk(
	out(k.selUsrId, "options"),
	inp(k.initView, "data"),
)
def vw_Init(dta_init):
	opts = [{"label": "All Users", "value": ""}]
	usrs = db.psql.fetchUsers()
	if usrs and len(usrs) > 0:
		for usr in usrs: opts.append({"label": usr.name, "value": usr.id})

	lg.info(f"[vw] init users[{len(usrs)}]")

	return opts


#========================================================================
# Handle filter changes - reset to page 1
#========================================================================
@cbk(
	out(pager.id.store(k.pagerMain), "data", allow_duplicate=True),
	[
		inp(k.selUsrId, "value"),
		inp(k.selFilter, "value"),
		inp(k.cbxFav, "value"),
		inp(k.schKeyword, "value"),
		inp(k.schPath, "value"),
		inp(k.cbxArc, "value"),
		inp(k.cbxLive, "value"),
	],
	ste(pager.id.store(k.pagerMain), "data"),
	prevent_initial_call=True
)
def vw_OnOptChg(usrId, opts, cbxFav, schKey, schPath, cbxArc, cbxLive, dta_pgr):
	pgr = Pager.fromDic(dta_pgr)

	# Update total count based on filters
	total = db.pics.countFiltered(
		usrId=usrId,
		opts=opts,
		search=schKey,
		pathFilter=schPath,
		favOnly=cbxFav,
		arcOnly=cbxArc,
		liveOnly=cbxLive
	)

	# Reset to page 1 when filter changes
	pgr.idx = 1
	pgr.cnt = total

	lg.info(f"[vw] Filter changed, total: {total}")

	return pgr.toDict()


#========================================================================
# Handle photo grid loading when pager changes
#========================================================================
@cbk(
	out(k.grid, "children"),
	[
		inp(pager.id.store(k.pagerMain), "data"),
		inp(k.selUsrId, "value"),
		inp(k.selFilter, "value"),
		inp(k.schKeyword, "value"),
		inp(k.schPath, "value"),
		inp(k.cbxFav, "value"),
		inp(k.cbxArc, "value"),
		inp(k.cbxLive, "value"),
		inp(k.cbxGridInfo, "value"),
		inp(ks.sto.cnt, "data"),
	],
	prevent_initial_call="initial_duplicate"
)
def vw_Load(dta_pgr, usrId, filOpt, shKey, shPath, onlyFav, onlyArc, onlyLive, showGridInfo, dta_cnt):
	db.dto.showGridInfo = showGridInfo
	if not dta_pgr: return noUpd

	cnt = models.Cnt.fromDic(dta_cnt)
	pgr = Pager.fromDic(dta_pgr)

	if cnt.ass <= 0: return dbc.Alert("No photos available", color="secondary", className="text-center")

	photos = db.pics.getFiltered(usrId, filOpt, shKey, shPath, onlyFav, onlyArc, onlyLive, pgr.idx, pgr.size)

	if photos and len(photos) > 0: lg.info(f"[vg:load] Loaded {len(photos)} photos for page {pgr.idx}")
	else:
		lg.info(f"[vg:load] No photos found for page {pgr.idx}")
		return dbc.Alert("No photos found matching your criteria", color="info", className="text-center")

	grid = gv.mkGrd(photos, maker=lambda a: gv.cards.mk(a, False))

	return grid

#========================================================================
# Click Delete
#========================================================================
@cbk(
	out(ks.sto.mdl, 'data', allow_duplicate=True),
	inp({"type": "asset-del", "aid": ALL}, "n_clicks"),
	ste(ks.sto.tsk, 'data'),
	prevent_initial_call=True
)
def vw_OnDel(clks, dta_tsk):
	if not clks or not any(clks): return noUpd

	tsk = models.Tsk.fromDic(dta_tsk)

	if tsk.id: return noUpd
	src = getTrgId()
	aid = src.get('aid')

	lg.info(f'aid: {aid}')

	mdl = models.Mdl()
	mdl.id = ks.pg.view
	mdl.cmd = ks.cmd.view.assDel
	mdl.args = {'aid': aid}
	mdl.msg = f"Are you sure delete Asset #{aid} ?"

	return mdl.toDict()

#------------------------------------------------------------------------
#------------------------------------------------------------------------


#========================================================================
# task acts
#========================================================================
from mod import mapFns
from mod.models import IFnProg

#------------------------------------------------------------------------
def onAssetDel(doReport: IFnProg, sto: models.ITaskStore):
	nfy, cnt, tsk = sto.nfy, sto.cnt, sto.tsk

	import db
	import immich

	try:
		aid = tsk.args.get('aid')
		msg = f"[Assets] Success delete #{aid}"
		if not aid: raise RuntimeError(f'No AutoId to delete')

		ass = db.pics.getByAutoId(aid)

		with psql.mkConn() as conn:
			with conn.cursor() as cur:
				immich.trashByAssets([ass], cur)
				conn.commit()

		db.pics.deleteBy([ass])
		db.vecs.deleteBy([aid])

		cnt.refreshFromDB()

		return sto, msg
	except Exception as e:
		msg = f"Failed to delete asset: {str(e)}"
		nfy.error(msg)
		raise RuntimeError(msg)


#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.view.assDel] = onAssetDel


ccbk(
	cbkFn("ui", "toggleGridInfo"),
	out({"type": "dummy", "id": "grid-info-view"}, "children"),
	inp(k.cbxGridInfo, "value"),
	prevent_initial_call=False
)
