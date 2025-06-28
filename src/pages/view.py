import db
import json
from conf import ks
from dsh import dash, htm, dcc, cbk, dbc, inp, out, ste, getTrgId, noUpd, ALL
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
    cbxFav = "inp-favorites"
    cbxArc = "inp-archived"

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
    try:
        total = db.pics.count()
    except:
        total = 0

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
                ]),

                dbc.Row([


                    dbc.Col([
                        dbc.Label("Search"),
                        dbc.Input(id=k.schKeyword, type="text", placeholder="Search by filename...", className="mb-2"),
                    ], width=4),

                    dbc.Col([
                        dbc.Checkbox(id=k.cbxFav, label="Favorites", value=False, className="mt-2"),
                        dbc.Checkbox(id=k.cbxArc, label="Archived", value=False, className="mt-2"),
                    ], width=8),
                ]),

                dbc.Row([
                    dbc.Col([
                    ], width=12),
                ]),
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
        for usr in usrs:
            opts.append({"label": usr.name, "value": usr.id})

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
    ],
    ste(pager.id.store(k.pagerMain), "data"),
    prevent_initial_call=True
)
def vw_OnOptChg( usrId, opts, cbxFav, schKey, dta_pgr):
    pgr = Pager.fromDic(dta_pgr)

    # Update total count based on filters
    total = db.pics.countFiltered(
        usrId=usrId,
        opts=opts,
        search=schKey,
        favOnly=cbxFav
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
        inp(k.cbxFav, "value"),
        inp(ks.sto.cnt, "data"),
    ],
    prevent_initial_call="initial_duplicate"
)
def vw_Load(dta_pgr, usrId, filOpt, shKey, onlyFav, dta_cnt):
    if not dta_pgr: return noUpd

    cnt = models.Cnt.fromDic(dta_cnt)
    pgr = Pager.fromDic(dta_pgr)

    if cnt.ass <= 0:
        return dbc.Alert("No photos available", color="secondary", className="text-center")

    photos = db.pics.getFiltered(usrId, filOpt, shKey, onlyFav, pgr.idx, pgr.size)

    if photos and len(photos) > 0:
        lg.info(f"[vg:load] Loaded {len(photos)} photos for page {pgr.idx}")
    else:
        lg.info(f"[vg:load] No photos found for page {pgr.idx}")
        return dbc.Alert("No photos found matching your criteria", color="info", className="text-center")

    grid = gv.mkGrd(photos, maker=lambda a: gv.cards.mk(a, False) )

    return grid

#========================================================================
# Click Delete
#========================================================================
@cbk(
    out(ks.sto.mdl, 'data', allow_duplicate=True),
    inp({"type": "asset-del", "aid":ALL}, "n_clicks"),
    ste(ks.sto.tsk, 'data'),
    prevent_initial_call=True
)
def vw_OnDel( clks, dta_tsk ):

    if not clks or not any(clks): return noUpd

    tsk = models.Tsk.fromDic(dta_tsk)

    if tsk.id: return noUpd
    src = json.loads(getTrgId())
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
        db.pics.deleteBy([ass])
        db.vecs.deleteBy([aid])
        immich.trashByAssets([ass])

        cnt.refreshFromDB()

        return sto, msg
    except Exception as e:
        msg = f"Failed to clear user data: {str(e)}"
        nfy.error(msg)
        raise RuntimeError(msg)


#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.view.assDel] = onAssetDel

