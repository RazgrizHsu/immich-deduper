import traceback
from typing import Optional
import time

import immich
import db
from conf import ks, co
from dsh import dash, htm, dcc, dbc, inp, out, ste, getTrgId, noUpd, ctx, ALL
from dsh import cbk, ccbk, cbkFn
from util import log
from mod import mapFns, models, tskSvc
from mod.models import Mdl, Now, Cnt, Nfy, Pager, Tsk, Ste, PgSim

from ui import pager, cardSets, gv

lg = log.get(__name__)

# Debug flag for verbose logging
DEBUG = False

dash.register_page(
    __name__,
    path=f'/{ks.pg.similar}',
    path_template=f'/{ks.pg.similar}/<autoId>',
    title=f"{ks.title}: " + ks.pg.similar.name,
)


class k:
    assFromUrl = 'sim-AssFromUrl'

    txtCntRs = 'sim-txt-cnt-records'
    txtCntOk = 'sim-txt-cnt-ok'
    txtCntNo = 'sim-txt-cnt-no'
    txtCntSel = 'sim-txt-cnt-sel'

    btnAllSelect = 'sim-btn-AllSelect'
    btnAllCancel = 'sim-btn-AllCancel'
    btnExportIds = 'sim-btn-ExportIds'

    btnFind = "sim-btn-fnd"
    btnClear = "sim-btn-clear"
    btnReset = "sim-btn-reset"
    btnRmSel = "sim-btn-RmSel"
    btnOkSel = "sim-btn-OkSel"
    btnOkAll = "sim-btn-OkAll"
    btnRmAll = "sim-btn-RmAll"
    cbxNChkOkAll = "sim-cbx-NChk-OkAll"
    cbxNChkRmSel = "sim-cbx-NChk-RmSel"
    cbxNChkOkSel = "sim-cbx-NChk-OkSel"
    cbxNChkRmAll = "sim-cbx-NChk-RmAll"


    tabs = 'sim-tabs'
    tabCur = "tab-current"
    tabPnd = "tab-pend"
    pagerPnd = "sim-pager-pnd"

    gvSim = "sim-gvSim"
    gvPnd = 'sim-gvPnd'

    @staticmethod
    def id(k): return { "type":"sim", "id":f"{k}" }


#========================================================================
def layout(autoId=None):
    # return flask.redirect('/target-page') #auth?

    guideAss: Optional[models.Asset] = None

    if autoId:
        lg.info(f"[sim] from url autoId[{autoId}]")
        try:

            guideAss = db.pics.getByAutoId(autoId)
            if guideAss:
                lg.info(f"[sim] =============>>>> set target assetId[{guideAss.id}]")
        except:
            lg.error(f"[sim] not found asset from aid[{autoId}]", exc_info=True)

    import ui
    return ui.renderBody([
        #====== top start =======================================================
        dcc.Store(id=k.assFromUrl, data=guideAss.toDict() if guideAss else {}),

        # 客戶端選擇狀態管理的 dummy 元素
        htm.Div(id={"type": "dummy-output", "id": "selection"}, style={"display": "none"}),
        htm.Div(id={"type": "dummy-output", "id": "init-selection"}, style={"display": "none"}),

        htm.Div([
            htm.H3(f"{ks.pg.similar.name}"),
            htm.Small(f"{ks.pg.similar.desc}", className="text-muted")
        ], className="body-header"),


        dbc.Row([
            dbc.Col([
                #------------------------------------------------------------------------
                cardSets.renderThreshold(),
                cardSets.renderAutoSelect(),
                #------------------------------------------------------------------------
            ], width=5),

            dbc.Col([

                cardSets.renderCard(),

                dbc.Row([
                    dbc.Col([
                        dbc.Button(f"Find Similar", id=k.btnFind, color="primary", className="w-100", disabled=True),
                        htm.Br(),
                        htm.Small("No similar found → auto-mark resolved", className="ms-2 me-2")
                    ], width=6),

                    dbc.Col([
                        dbc.Button("Clear record & Keep resloved", id=k.btnClear, color="danger me-1", className="w-100 mb-1", disabled=True),
                        dbc.Button("Reset records", id=k.btnReset, color="danger", className="w-58", disabled=True),
                    ], width=6, className="text-end"),
                ], className="mt-3"),

            ], width=7),
        ], className=""),

        #====== top end =========================================================
    ], [
        #====== bottom start=====================================================

        #------------------------------------------------------------------------
        # Tabs
        #------------------------------------------------------------------------
        htm.Div([

            dbc.Tabs(
                id=k.tabs,
                active_tab=k.tabCur,
                children=[
                    dbc.Tab(
                        label="current", tab_id=k.tabCur,
                        children=[

                            # Action buttons
                            htm.Div([

                                htm.Div([

                                    dbc.Button( [ htm.Span( className="fake-checkbox checked" ), "select All"], id=k.btnAllSelect, size="sm", color="secondary", disabled=True ),
                                    dbc.Button( [ htm.Span( className="fake-checkbox" ),"Deselect All"], id=k.btnAllCancel, size="sm", color="secondary", disabled=True ),
                                    dbc.Button("Export IDs", id=k.btnExportIds, size="sm", color="info", disabled=True ),

                                ], className="left"),


                                htm.Div([

                                    htm.Div([
                                        dbc.Checkbox(id=k.cbxNChkOkSel, label="No-Confirm", className="sm"),
                                        htm.Br(),
                                        dbc.Button("Keep Select, Delete others", id=k.btnOkSel, color="success", size="sm", disabled=True),
                                    ]),

                                    htm.Div([
                                        dbc.Checkbox(id=k.cbxNChkRmSel, label="No-Confirm", className="sm"),
                                        htm.Br(),
                                        dbc.Button("Del Select, Keep others", id=k.btnRmSel, color="danger", size="sm", disabled=True),
                                    ]),

                                    htm.Div([
                                        dbc.Checkbox(id=k.cbxNChkOkAll, label="No-Confirm", className="sm"),
                                        htm.Br(),
                                        dbc.Button("✅ Keep All", id=k.btnOkAll, color="success", size="sm", disabled=True),
                                    ]),

                                    htm.Div([
                                        dbc.Checkbox(id=k.cbxNChkRmAll, label="No-Confirm", className="sm"),
                                        htm.Br(),
                                        dbc.Button("❌ Delete All", id=k.btnRmAll, color="danger", size="sm", disabled=True),
                                    ]),

                                ], className="right"),


                            ],
                                className="tab-acts"
                            ),


                            dbc.Spinner(
                                htm.Div(id=k.gvSim),
                                color="success", type="border", spinner_style={"width": "3rem", "height": "3rem"},
                            ),

                            # Floating Goto Top Button
                            htm.Button(
                                "↑ Top",
                                id="sim-goto-top-btn",
                                className="goto-top-btn",
                                style={"display": ""}
                            ),
                        ]
                    ),
                    dbc.Tab(
                        label="pending",
                        tab_id=k.tabPnd,
                        id=k.tabPnd,
                        disabled=True,
                        children=[
                            htm.Div([
                                # top pager
                                *pager.createPager(pgId=k.pagerPnd, idx=0, btnSize=9, className="mb-3"),

                                dbc.Spinner(
                                htm.Div(id=k.gvPnd),
                                color="success", type="border", spinner_style={"width": "3rem", "height": "3rem"},
                                ),

                                # bottom pager
                                *pager.createPager(pgId=k.pagerPnd, idx=1, btnSize=9, className="mt-3"),

                                # Main pager (store only)
                                *pager.createStore(pgId=k.pagerPnd),
                            ], className="text-center")
                        ]
                    ),
                ]
            )
        ],
            className="ITab"
        ),

        #====== bottom end ======================================================
    ])



#========================================================================
# callbacks
#========================================================================

pager.regCallbacks(k.pagerPnd)


#------------------------------------------------------------------------
# Sync tab changes to now state
#------------------------------------------------------------------------
@cbk(
    out(ks.sto.now, "data", allow_duplicate=True),
    inp(k.tabs, "active_tab", ),
    ste(ks.sto.now, "data"),
    prevent_initial_call=True
)
def sim_OnTabChange(active_tab, dta_now):
    if not active_tab or not dta_now: return noUpd

    now = Now.fromDic(dta_now)

    if now.sim.activeTab == active_tab: return noUpd

    lg.info(f"[sim:tab] Tab changed to: {active_tab} (from: {now.sim.activeTab})")

    patch = dash.Patch()
    patch['sim']['activeTab'] = active_tab
    return patch



#------------------------------------------------------------------------
# Handle pager changes - reload pending data
#------------------------------------------------------------------------
@cbk(
    [
        out(k.gvPnd, "children", allow_duplicate=True),
        out(ks.sto.now, "data", allow_duplicate=True),
    ],
    inp(pager.id.store(k.pagerPnd), "data"),
    ste(ks.sto.now, "data"),
    prevent_initial_call=True
)
def sim_onPagerChanged(dta_pgr, dta_now):
    if not dta_pgr or not dta_now: return noUpd.by(2)

    now = Now.fromDic(dta_now)
    pgr = Pager.fromDic(dta_pgr)

    # Check if we're already on this page with same data
    oldPgr = now.sim.pagerPnd
    if oldPgr and oldPgr.idx == pgr.idx and oldPgr.size == pgr.size and oldPgr.cnt == pgr.cnt:
        if DEBUG: lg.info(f"[sim:pager] Already on page {pgr.idx}, skipping reload")
        return noUpd.by(2)

    now.sim.pagerPnd = pgr

    paged = db.pics.getPagedPending(page=pgr.idx, size=pgr.size)
    now.sim.assPend = paged

    lg.info(f"[sim:pager] paged: {pgr.idx}/{(pgr.cnt + pgr.size - 1) // pgr.size}, got {len(paged)} items")

    gvPnd = gv.mkPndGrd(now.sim.assPend, onEmpty=[
        dbc.Alert("No pending items on this page", color="secondary", className="text-center"),
    ])

    return gvPnd, now.toDict()



#------------------------------------------------------------------------
# assert from url
#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.now, "data", allow_duplicate=True),
        out(ks.sto.tsk, "data", allow_duplicate=True),
    ],
    inp(k.assFromUrl, "data"),
    [
        ste(ks.sto.now, "data"),
    ],
    prevent_initial_call="initial_duplicate"
)
def sim_SyncUrlAssetToNow(dta_ass, dta_now):
    now = Now.fromDic(dta_now)

    if not dta_ass:
        if not now.sim.assFromUrl: return noUpd.by(2)

        patch = dash.Patch()
        patch['sim']['assFromUrl'] = None
        return patch, noUpd

    ass = models.Asset.fromDic(dta_ass)

    lg.info(f"[sim:sync] asset from url: #{ass.autoId} id[{ass.id}]")

    now.sim.assFromUrl = ass
    now.sim.assAid = ass.autoId

    mdl = Mdl()
    mdl.id = ks.pg.similar
    mdl.cmd = ks.cmd.sim.fnd
    mdl.msg = f'Search images similar to {ass.autoId}'

    tsk = mdl.mkTsk()

    lg.info(f"[sim:sync] to task: {tsk}")

    return now.toDict(), tsk.toDict()


#------------------------------------------------------------------------
# onStatus
#------------------------------------------------------------------------
@cbk(
    [
        out(k.gvSim, "children"),
        out(k.gvPnd, "children"),
        out(ks.sto.now, "data", allow_duplicate=True),
        out(pager.id.store(k.pagerPnd), "data", allow_duplicate=True),
        out(k.tabPnd, "disabled"),
        out(k.tabPnd, "label"),
        out(k.tabs, "active_tab", allow_duplicate=True),
    ],
    inp(ks.sto.now, "data"),
    [
        ste(ks.sto.cnt, "data"),
    ],
    prevent_initial_call="initial_duplicate"
)
def sim_Load(dta_now, dta_cnt):
    now = Now.fromDic(dta_now)
    cnt = Cnt.fromDic(dta_cnt)

    trgId = getTrgId()
    if trgId: lg.info(f"[sim:load] load, trig: [ {trgId} ]")

    cntNo, cntOk, cntPn = cnt.simNo, cnt.simOk, cnt.simPnd

    gvSim = []

    # Check multi mode from dto settings
    if db.dto.muod:
        gvSim = gv.mkGrdGrps(now.sim.assCur, onEmpty=[
            dbc.Alert("No grouped results found..", color="secondary", className="text-center m-5"),
        ])
    else:
        gvSim = gv.mkGrd(now.sim.assCur, onEmpty=[
            dbc.Alert("Please find the similar images..", color="secondary", className="text-center m-5"),
        ])

    # Initialize or get pager
    pgr = now.sim.pagerPnd
    if not pgr:
        pgr = Pager(idx=1, size=20)
        now.sim.pagerPnd = pgr

    # Update pager total count
    pagerData = None
    oldPn = pgr.cnt
    if pgr.cnt != cntPn:
        pgr.cnt = cntPn
        # Keep current page if still valid, otherwise reset to last valid page
        totalPages = (cntPn + pgr.size - 1) // pgr.size if cntPn > 0 else 1
        if pgr.idx > totalPages: pgr.idx = max(1, totalPages)
        now.sim.pagerPnd = pgr
        # Only update pager store if count actually changed
        if oldPn != cntPn: pagerData = pgr

    lg.info(f"--------------------------------------------------------------------------------")
    lg.info(f"[sim:load] trig[{trgId}] muod[{db.dto.muod}] cntNo[{cntNo}] cntOk[{cntOk}] cntPn[{cntPn}]({oldPn}) assCur[{len(now.sim.assCur)}] assAid[{now.sim.assAid}]")

    # Load pending data - reload if count changed or no data
    needReload = False
    if cntPn > 0:
        if not now.sim.assPend or len(now.sim.assPend) == 0:
            needReload = True
        elif oldPn != cntPn:
            needReload = True
            lg.info(f"[sim:load] Pending count changed from {oldPn} to {cntPn}, reloading data")
    else:
        needReload = True

    if needReload:
        paged = db.pics.getPagedPending(page=pgr.idx, size=pgr.size)
        lg.info(f"[sim:load] pend reload, idx[{pgr.idx}] size[{pgr.size}] got[{len(paged)}]")
        now.sim.assPend = paged

    # Only rebuild gvPnd if pending data changed
    if needReload:
        gvPnd = gv.mkPndGrd(now.sim.assPend, onEmpty=[
            dbc.Alert("Please find the similar images..", color="secondary", className="text-center m-5"),
        ])
    else:
        gvPnd = noUpd

    # Update pending tab state based on cntPn
    tabDisabled = cntPn < 1
    tabLabel = f"pending ({cntPn})" if cntPn >= 1 else "pending"

    # Only update now if there were actual changes
    nowChanged = needReload or (pagerData is not None)
    nowDict = now.toDict() if nowChanged else noUpd

    activeTab = now.sim.activeTab if now.sim.activeTab else k.tabCur

    return [
        gvSim, gvPnd,
        nowDict,
        pagerData.toDict() if pagerData else noUpd,
        tabDisabled, tabLabel, activeTab
    ]


#------------------------------------------------------------------------
# Update status counters - Using CLIENT-SIDE callbacks for performance
#------------------------------------------------------------------------

ccbk(
    cbkFn( "similar", "onCardSelectClicked" ),
    out(ks.sto.ste, "data"),
    [inp({"type": "card-select", "id": ALL}, "n_clicks")],
    prevent_initial_call=True
)


#------------------------------------------------------------------------
# Initialize client-side selection state when assets load
#------------------------------------------------------------------------
ccbk(
    cbkFn( "similar", "onNowSyncToDummyInit" ),
    out({"type": "dummy-output", "id": "init-selection"}, "children"),
    inp(ks.sto.now, "data"),
    inp(ks.sto.ste, "data"),
    prevent_initial_call="initial_duplicate"
)


#------------------------------------------------------------------------
# Update all button states based on current data
#------------------------------------------------------------------------
@cbk(
    [
        out(k.btnFind, "disabled"),
        out(k.btnClear, "disabled"),
        out(k.btnReset, "disabled"),
        out(k.btnOkAll, "disabled"),
        out(k.btnRmAll, "disabled"),
        out(k.btnRmSel, "disabled"),
        out(k.btnOkSel, "disabled"),
        out(k.btnExportIds, "disabled"),
    ],
    [
        inp(ks.sto.now, "data"),
        inp(ks.sto.ste, "data"),
        inp(ks.sto.cnt, "data"),
    ],
    prevent_initial_call="initial_duplicate"
)
def sim_UpdateButtons(dta_now, dta_ste, dta_cnt):
    now = Now.fromDic(dta_now)
    ste = Ste.fromDic(dta_ste) if dta_ste else Ste()
    cnt = Cnt.fromDic(dta_cnt)

    from mod.mgr.tskSvc import mgr
    isTaskRunning = False
    if mgr:
        for _, info in mgr.list().items():
            if info.status.value in ['pending', 'running']:
                isTaskRunning = True
                break

    cntNo = cnt.ass - cnt.simOk if cnt else 0
    cntPn = cnt.simPnd if cnt else 0
    disFind = cntNo <= 0 or (cntPn >= cntNo) or isTaskRunning

    cntSrchd = db.pics.countHasSimIds(isOk=0) if not isTaskRunning else 0
    disClear = cntSrchd <= 0 or isTaskRunning

    cntOk = cnt.simOk if cnt else 0
    disReset = cntOk <= 0 and cntPn <= 0 or isTaskRunning

    cntAssets = len(now.sim.assCur) if now.sim.assCur else 0
    disOk = cntAssets <= 0
    disDel = cntAssets <= 0

    cntSel = len(ste.selectedIds) if ste.selectedIds else 0
    disRm = cntSel == 0
    disRS = cntSel == 0

    disExport = cntAssets <= 0

    # lg.info(f"[sim:UpdBtns] disFind[{disFind}]")

    return disFind, disClear, disReset, disOk, disDel, disRm, disRS, disExport


#------------------------------------------------------------------------
# Handle group view button click
#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.now, "data", allow_duplicate=True),
        out(k.tabs, "active_tab", allow_duplicate=True),  # Switch to current tab
    ],
    inp({"type": "btn-view-group", "id": ALL}, "n_clicks"),
    [
        ste(ks.sto.now, "data"),
    ],
    prevent_initial_call=True
)
def sim_OnSwitchViewGroup(clks, dta_now):
    if not ctx.triggered: return noUpd.by(2)

    # Check if any button was actually clicked
    if not any(clks): return noUpd.by(2)

    now = Now.fromDic(dta_now)

    trgId = ctx.triggered_id

    if not trgId: return noUpd.by(2)

    assId = trgId["id"]

    lg.info(f"[sim:vgrp] switch: id[{assId}] clks[{clks}]")

    asset = db.pics.getById(assId)
    if not asset: return noUpd.by(2)

    now.sim.assAid = asset.autoId
    now.sim.assCur = db.pics.getSimAssets(asset.autoId, db.dto.rtree)

    if DEBUG: lg.info(f"[sim:vgrp] Loaded {len(now.sim.assCur)} assets for group")

    return now.toDict(), k.tabCur  # Switch to current tab


#========================================================================
# trigger modal
#========================================================================
@cbk(
    [
        out(ks.sto.nfy, "data", allow_duplicate=True),
        out(ks.sto.now, "data", allow_duplicate=True),
        out(ks.sto.mdl, "data", allow_duplicate=True),
        out(ks.sto.tsk, "data", allow_duplicate=True),
        out(ks.sto.ste, "data", allow_duplicate=True),
    ],
    [
        inp(k.btnFind, "n_clicks"),
        inp(k.btnClear, "n_clicks"),
        inp(k.btnReset, "n_clicks"),
        inp(k.btnRmSel, "n_clicks"),
        inp(k.btnOkSel, "n_clicks"),
        inp(k.btnOkAll, "n_clicks"),
        inp(k.btnRmAll, "n_clicks"),
    ],
    [
        ste(ks.sto.now, "data"),
        ste(ks.sto.cnt, "data"),
        ste(ks.sto.mdl, "data"),
        ste(ks.sto.tsk, "data"),
        ste(ks.sto.nfy, "data"),
        ste(ks.sto.ste, "data"),
        ste(k.cbxNChkOkAll, "value"),
        ste(k.cbxNChkRmSel, "value"),
        ste(k.cbxNChkOkSel, "value"),
        ste(k.cbxNChkRmAll, "value"),
    ],
    prevent_initial_call=True
)
def sim_RunModal(
    clk_fnd, clk_clr, clk_rst, clk_rm, clk_rs, clk_ok, clk_ra,
    dta_now, dta_cnt, dta_mdl, dta_tsk, dta_nfy, dta_ste,
    nchkOkAll, nchkRmSel, ncRS, ncRA
):
    if not clk_fnd and not clk_clr and not clk_rst and not clk_rm and not clk_rs and not clk_ok and not clk_ra:
        lg.info( f"[sim:RunModal] fnd[{clk_fnd}] clr[{clk_clr}] rst[{clk_rst}] rm[{clk_rm}] rs[{clk_rs}] ok[{clk_ok}] ra[{clk_ra}]" )
        return noUpd.by(5)

    trgId = getTrgId()

    now = Now.fromDic(dta_now)
    cnt = Cnt.fromDic(dta_cnt)
    mdl = Mdl.fromDic(dta_mdl)
    tsk = Tsk.fromDic(dta_tsk)
    nfy = Nfy.fromDic(dta_nfy)
    ste = Ste.fromDic(dta_ste)

    retNow, retTsk, retSte = noUpd, noUpd, noUpd



    # Check if any task is already running
    from mod.mgr.tskSvc import mgr
    if mgr:
        for _, info in mgr.list().items():
            if info.status.value in ['pending', 'running']:
                nfy.warn(f"Task already running, please wait for it to complete")
                return noUpd.by(5).upd(0, nfy)

    if tsk.id:
        if mgr and mgr.getInfo(tsk.id):
            ti = mgr.getInfo(tsk.id)
            if ti and ti.status in ['pending', 'running']:
                nfy.warn(f"[similar] Task already running: {tsk.id}")
                return noUpd.by(5).upd(0, nfy)
            # lg.info(f"[similar] Clearing completed task: {tsk.id}")
            tsk.id = None
            tsk.cmd = None

    lg.info(f"[similar] trig[{trgId}] tsk[{tsk}]")

    #------------------------------------------------------------------------
    if trgId == k.btnClear:
        cntRs = db.pics.countHasSimIds(isOk=0)
        if cntRs <= 0:
            nfy.warn(f"[similar] No search records to clear")
            return noUpd.by(5).upd(0, nfy)

        mdl.reset()
        mdl.id = ks.pg.similar
        mdl.cmd = ks.cmd.sim.clear
        mdl.msg = [
            f"Clear search records but keep resolved items?", htm.Br(),
            f"Will clear ({cntRs}) search records", htm.Br(),
            htm.B("Resolved items (simOk=1) will be kept"), htm.Br(),
        ]

    #------------------------------------------------------------------------
    elif trgId == k.btnReset:
        cntOk = db.pics.countSimOk(isOk=1)
        cntRs = db.pics.countHasSimIds()
        if cntOk <= 0 and cntRs <= 0:
            nfy.warn(f"[similar] DB does not contain any similarity records")
            return noUpd.by(5).upd(0, nfy)

        mdl.reset()
        mdl.id = ks.pg.similar
        mdl.cmd = ks.cmd.sim.reset
        mdl.msg = [
            f"Are you sure you want to reset all records?", htm.Br(),
            f"include resolved({cntOk}) and search({cntRs})", htm.Br(),
            htm.B("This operation cannot be undone"), htm.Br(),
            "You may need to perform all similarity searches again."
        ]

    #------------------------------------------------------------------------
    elif trgId == k.btnRmSel:
        assSel = ste.getSelected(now.sim.assCur)
        assAll = now.sim.assCur
        cnt = len(assSel)

        lg.info(f"[sim:delSels] {cnt} assets selected")

        if cnt > 0:
            mdl.reset()
            mdl.id = ks.pg.similar
            mdl.cmd = ks.cmd.sim.selRm
            mdl.msg = [
                f"Are you sure you want to Delete select images( {cnt} ) and Keep others( {len(assAll)-cnt} )?", htm.Br(),
                htm.B("This operation cannot be undone"),
            ]

            if nchkRmSel:
                retTsk = mdl.mkTsk()
                mdl.reset()

    #------------------------------------------------------------------------
    elif trgId == k.btnOkSel:
        assSel = ste.getSelected(now.sim.assCur)
        assAll = now.sim.assCur
        cnt = len(assSel)

        lg.info(f"[sim:resolveSels] {cnt} assets selected")

        if cnt > 0:
            mdl.reset()
            mdl.id = ks.pg.similar
            mdl.cmd = ks.cmd.sim.selOk
            mdl.msg = [
                f"Are you sure you want to Resolve selected images( {cnt} ) and Delete others( {len(assAll) - cnt} )?", htm.Br(),
                htm.B("This operation cannot be undone"),
            ]

            if ncRS:
                retTsk = mdl.mkTsk()
                mdl.reset()

    #------------------------------------------------------------------------
    elif trgId == k.btnRmAll:
        assSel = now.sim.assCur
        cnt = len(assSel)

        lg.info(f"[sim:delAll] {cnt} assets to delete")

        if cnt > 0:
            mdl.reset()
            mdl.id = ks.pg.similar
            mdl.cmd = ks.cmd.sim.allRm
            mdl.msg = [
                f"Are you sure you want to Delete ALL current images( {cnt} )?", htm.Br(),
                htm.B("This operation cannot be undone"),
            ]

            if ncRA:
                retTsk = mdl.mkTsk()
                mdl.reset()

    #------------------------------------------------------------------------
    elif trgId == k.btnOkAll:
        assSel = now.sim.assCur
        cnt = len(assSel)

        lg.info(f"[sim:reslove] {cnt} assets")

        if cnt > 0:
            mdl.reset()
            mdl.id = ks.pg.similar
            mdl.cmd = ks.cmd.sim.allOk
            mdl.msg = f"Are you sure mark resloved current images( {cnt} )?"

            if nchkOkAll:
                retTsk = mdl.mkTsk()
                mdl.reset()

    #------------------------------------------------------------------------
    elif trgId == k.btnFind:

        retSte = ste.clear()
        if cnt.vec <= 0:
            nfy.error("No vector data to process")
            now.sim.clearAll()
            return noUpd.by(5).upd( 0, [nfy, now] )

        thMin = db.dto.thMin

        lg.info(f"[thMin] min[{thMin}] max[1.0]")

        asset: Optional[models.Asset] = None

        # asset from url
        isFromUrl = False
        if now.sim.assFromUrl:
            assSel = now.sim.assFromUrl  #consider read from db again?
            if assSel:
                if assSel.simOk != 1:
                    lg.info(f"[sim] use selected asset id[{assSel.id}]")
                    asset = assSel
                    isFromUrl = True
                else:
                    nfy.info(f"[sim] the asset #{assSel.autoId} already resolved")
                    now.sim.assFromUrl = None
                    return noUpd.by(5).upd( 0, [nfy, now] )
            else:
                nfy.warn(f"[sim] not found dst assetId[{now.sim.assFromUrl}]")
                now.sim.assFromUrl = None
                return noUpd.by(5).upd( 0, [nfy, now] )

        # find from db
        if not asset:
            assSel = db.pics.getAnyNonSim()
            if assSel:
                asset = assSel
                lg.info(f"[sim] found non-simOk #{assSel.autoId} assetId[{assSel.id}]")

        if not isFromUrl:
            now.sim.clearAll()
            retNow = now

        if not asset:
            nfy.warn(f"[sim] not any asset to find..")
        else:
            now.sim.assAid = asset.autoId

            mdl.id = ks.pg.similar
            mdl.cmd = ks.cmd.sim.fnd
            tsk = mdl.mkTsk()
            mdl.reset()

            lg.info(f"[sim:run] now.sim.assAid[{now.sim.assAid}]")

            # only find auto trigger tsk
            retTsk = tsk
            retNow = now


    lg.info(f"[similar] modal[{mdl.id}] cmd[{mdl.cmd}]")

    return noUpd.by( 5 ).upd( 0, [nfy, retNow, mdl, retTsk, retSte] )


#========================================================================
# task acts
#========================================================================
from mod.models import IFnProg


def queueAutoNext(sto: models.ITaskStore):
    tsk = sto.tsk

    ass = db.pics.getAnyNonSim()
    if ass:
        lg.info(f"[sim] auto found non-simOk assetId[{ass.id}]")

        mdl = models.Mdl()
        mdl.id = ks.pg.similar
        mdl.cmd = ks.cmd.sim.fnd
        mdl.args = {'thMin': db.dto.thMin}

        ntsk = mdl.mkTsk()
        ntsk.args['assetId'] = ass.id

        sto.tsk.nexts.append(ntsk)

        sto.tsk = tsk
        # nfy.success([f"Auto-Find next: #{ass.autoId}"])


def sim_FindSimilar(doReport: IFnProg, sto: models.ITaskStore):
    from db import sim

    nfy, now, tsk = sto.nfy, sto.now, sto.tsk

    maxItems = db.dto.rtreeMax
    thMin = db.dto.thMin

    thMin = co.vad.float(thMin, 0.9)

    isFromUrl = now.sim.assFromUrl is not None and now.sim.assFromUrl.autoId is not None

    lg.info(f"[sim:fs] config maxItems[{maxItems}]")

    # Clear URL guidance to avoid duplicate searches
    if now.sim.assFromUrl:
        now.sim.assFromUrl = None

    try:
        lg.info(f"[sim:fs] now.sim.assAid[{now.sim.assAid}]")
        doReport(1, f"prepare..")

        # Find asset candidate
        try:
            asset = sim.findCandidate(now.sim.assAid, tsk.args)
        except RuntimeError as e:
            if "already searched" in str(e):
                now.sim.assCur = []
                return sto, [str(e)]
            raise e

        # search
        grps = sim.searchBy(asset, doReport, sto.isCancelled, isFromUrl)

        if not grps:
            nfy.info(f"No similar Threshold[{thMin}] groups found for asset #{asset.autoId}")
            return sto, f"No similar Threshold[{thMin}] groups found for asset #{asset.autoId}"

        if not grps[0].assets:
            nfy.info(f"Asset #{asset.autoId} no similar found")
            return sto, f"Asset #{asset.autoId} no similar found"

        # Auto mark single items as resolved
        db.pics.setSimAutoMark()

        assets = []
        for g in grps: assets.extend(g.assets)

        doReport(95, f"Finalizing {len(grps)} group(s) with {len(assets)} total assets")
        time.sleep(0.5)

        # Update state
        now.sim.assAid = asset.autoId
        now.sim.assCur = assets
        now.sim.activeTab = k.tabCur

        lg.info(f"[sim:fs] done, found {len(grps)} group(s) with {len(assets)} assets")
        lg.info(f"[sim:fs] assets autoIds: {[a.autoId for a in assets]}")

        if not now.sim.assCur: raise RuntimeError(f"No groups found")

        doReport(100, f"Completed finding {len(grps)} similar photo group(s)")

        # Generate completion message
        if db.dto.muod:
            mxGrp = db.dto.muod_Size

            msg = [f"Found {len(grps)} similar photo group(s) with {len(assets)} total photos"]
            if len(grps) >= mxGrp: msg.append(f"Reached maximum group limit ({mxGrp} groups).")
        else:
            root = grps[0].asset
            assert root is not None
            cntInfos = len(grps[0].bseInfos)
            cntAll = len(assets)
            hasRoot = any(a.autoId == root.autoId for a in assets)
            msg = [f"Found {cntInfos} similar, displaying {cntAll} for #{root.autoId} ({root.id})"]
            if not hasRoot:
                msg.append(f"⚠️ Root #{root.autoId} missing from display!")
            if cntAll > cntInfos:
                msg.append(f"include ({cntAll - cntInfos}) asset extra tree in similar tree.")
            if cntAll >= maxItems:
                msg.append(f"Reached maximum search limit ({maxItems} items).")

        # Auto-select assets if enabled
        lg.info(f"[sim:fs] Starting auto-selection check, enable={db.dto.ausl}")
        sto.ste.clear()
        autoSelectedIds = sim.getAutoSelectAuids(now.sim.assCur) if now.sim.assCur else []
        if autoSelectedIds:
            lg.info(f"[sim:fs] Auto-selected {len(autoSelectedIds)} assets: {autoSelectedIds}")
            sto.ste.selectedIds = autoSelectedIds
            sto.ste.cntTotal = len(now.sim.assCur)
            lg.info(f"[sim:fs] Updated ste store: selectedIds={sto.ste.selectedIds}, cntTotal={sto.ste.cntTotal}")
        else:
            lg.info(f"[sim:fs] No assets auto-selected")

        nfy.success(msg)
        return sto, msg

    except Exception as e:
        msg = f"[sim:fs] Similar search failed: {str(e)}"
        nfy.error(msg)
        lg.error(traceback.format_exc())
        now.sim.clearAll()
        sto.ste.clear()
        raise RuntimeError(msg)



def sim_ClearSims(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, tsk = sto.nfy, sto.now, sto.tsk

    try:
        keepSimOk = tsk.cmd == ks.cmd.sim.clear

        doReport(10, "Preparing to clear similarity records...")

        if keepSimOk:
            cntRs = db.pics.countHasSimIds(isOk=0)
            if cntRs <= 0:
                msg = "No search records to clear"
                lg.info(msg)
                nfy.info(msg)
                return sto, msg
        else:
            cntOk = db.pics.countSimOk(isOk=1)
            cntRs = db.pics.countHasSimIds()
            if cntOk <= 0 and cntRs <= 0:
                msg = "No similarity records to clear"
                lg.info(msg)
                nfy.info(msg)
                return sto, msg

        doReport(30, "Clearing similarity records from database...")

        db.pics.clearAllSimIds(keepSimOk=keepSimOk)

        doReport(90, "Updating dynamic data...")

        now.sim.assFromUrl = None
        now.sim.clearAll()
        sto.ste.clear()

        doReport(100, "Clear completed")

        if keepSimOk:
            msg = f"Successfully cleared search records but kept resolved items"
        else:
            msg = f"Successfully cleared all similarity records"

        lg.info(f"[sim_Clear] {msg}")
        nfy.success(msg)

        return sto, msg

    except Exception as e:
        msg = f"Failed to clear similarity records: {str(e)}"
        lg.error(f"[sim_Clear] {msg}")
        lg.error(traceback.format_exc())
        nfy.error(msg)
        raise RuntimeError(msg)



def sim_SelectedDelete(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, ste = sto.nfy, sto.now, sto.ste
    try:
        assAlls = now.sim.assCur
        assSels = ste.getSelected(assAlls) if ste else []
        assLefts = [a for a in assAlls if a.autoId not in {s.autoId for s in assSels}]

        cntSelect = len(assSels)
        msg = f"[sim] Delete Selected Assets( {cntSelect} ) Success!"

        if not assSels or cntSelect == 0: raise RuntimeError("Selected not found")

        db.pics.deleteBy(assSels)
        db.pics.setResloveBy(assLefts)  # set unselected to resloved
        immich.trashByAssets(assSels)

        now.sim.clearAll()
        sto.ste.clear()

        if not db.dto.autoNext:
            now.sim.activeTab = k.tabPnd
        else:
            queueAutoNext(sto)

        nfy.success(msg)

        return sto, msg
    except Exception as e:
        msg = f"[sim] Delete selected failed: {str(e)}"
        nfy.error(msg)
        lg.error(traceback.format_exc())
        now.sim.clearAll()
        sto.ste.clear()

        raise RuntimeError(msg)


def sim_SelectedReslove(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, ste = sto.nfy, sto.now, sto.ste
    try:
        assAlls = now.sim.assCur
        assSels = ste.getSelected(assAlls) if ste else []
        assOthers = [a for a in assAlls if a.autoId not in {s.autoId for s in assSels}]

        cntSelect = len(assSels)
        cntOthers = len(assOthers)
        msg = f"[sim] Resolve Selected Assets( {cntSelect} ) and Delete Others( {cntOthers} ) Success!"

        if not assSels or cntSelect == 0: raise RuntimeError("Selected not found")

        lg.info(f"[sim:selOk] reslove assets[{cntSelect}] delete[ {cntOthers} ]")

        if assOthers: db.pics.deleteBy(assOthers)
        db.pics.setResloveBy(assSels)

        if assOthers: immich.trashByAssets(assOthers)

        now.sim.clearAll()
        sto.ste.clear()

        if not db.dto.autoNext:
            now.sim.activeTab = k.tabPnd
        else:
            queueAutoNext(sto)

        return sto, msg
    except Exception as e:
        msg = f"[sim] Resolve selected failed: {str(e)}"
        nfy.error(msg)
        lg.error(traceback.format_exc())
        now.sim.clearAll()
        sto.ste.clear()

        raise RuntimeError(msg)


def sim_AllReslove(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt
    try:
        assets = now.sim.assCur
        cntAll = len(assets)
        msg = f"[sim] set Resloved Assets( {cntAll} ) Success!"

        if not assets or cnt == 0: raise RuntimeError("Current Assets not found")
        lg.info(f"[sim:allReslove] reslove assets[{cntAll}] ")

        db.pics.setResloveBy(assets)

        now.sim.clearAll()
        sto.ste.clear()

        if not db.dto.autoNext:
            now.sim.activeTab = k.tabPnd
        else:
            queueAutoNext(sto)

        return sto, msg
    except Exception as e:
        msg = f"[sim] Resloved All failed: {str(e)}"
        nfy.error(msg)
        lg.error(traceback.format_exc())
        now.sim.clearAll()
        sto.ste.clear()

        raise RuntimeError(msg)


def sim_AllDelete(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now = sto.nfy, sto.now
    try:
        assets = now.sim.assCur
        cntAll = len(assets)
        msg = f"[sim] Delete All Assets( {cntAll} ) Success!"

        if not assets or cntAll == 0: raise RuntimeError("Current Assets not found")

        lg.info(f"[sim:allDel] delete assets[{cntAll}] ")

        db.pics.deleteBy(assets)
        immich.trashByAssets(assets)

        now.sim.clearAll()
        sto.ste.clear()

        if not db.dto.autoNext:
            now.sim.activeTab = k.tabPnd
        else:
            queueAutoNext(sto)

        return sto, msg
    except Exception as e:
        msg = f"[sim] Delete all failed: {str(e)}"
        nfy.error(msg)
        lg.error(traceback.format_exc())
        now.sim.clearAll()
        sto.ste.clear()

        raise RuntimeError(msg)



#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.sim.fnd] = sim_FindSimilar
mapFns[ks.cmd.sim.clear] = sim_ClearSims
mapFns[ks.cmd.sim.reset] = sim_ClearSims
mapFns[ks.cmd.sim.selOk] = sim_SelectedReslove
mapFns[ks.cmd.sim.selRm] = sim_SelectedDelete
mapFns[ks.cmd.sim.allOk] = sim_AllReslove
mapFns[ks.cmd.sim.allRm] = sim_AllDelete
