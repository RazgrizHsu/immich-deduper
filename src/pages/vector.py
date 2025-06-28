import db
from conf import ks
import conf
from dsh import dash, htm, cbk, dbc, inp, out, ste, getTrgId, noUpd
from util import log
from mod import models, mapFns, tskSvc
from ui import cardSets

lg = log.get(__name__)

dash.register_page(
    __name__,
    path=f'/{ks.pg.vector}',
    title=f"{ks.title}: " + ks.pg.vector.name,
)

class K:
    selectQ = "vector-selectPhotoQ"
    btnDoVec = "vector-btnDoVec"
    btnClear = "vector-btnClear"


#========================================================================
def layout():
    import ui
    return ui.renderBody([
        #====== top start =======================================================

        htm.Div([
            htm.H3(f"{ks.pg.vector.name}"),
            htm.Small(f"{ks.pg.vector.desc}", className="text-muted")
        ], className="body-header"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Processing Settings"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Photo Quality"),
                                dbc.Select(
                                    id=K.selectQ,
                                    options=[
                                        {"label": "Thumbnail (Fast)", "value": ks.db.thumbnail},
                                        {"label": "Preview", "value": ks.db.preview},
                                    ],
                                    value=db.dto.photoQ,
                                    className="mb-3",
                                ),
                            ], width=12),
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                htm.Ul([
                                    htm.Li([htm.B("Thumbnail"), htm.Small(" Fastest, but with lower detail comparison accuracy"), ]),
                                    htm.Li([htm.B("Preview"), htm.Small(" Medium quality, generally the most balanced option"), ]),
                                ]),
                            ], width=12, className=""),
                        ], className="mb-0"),

                    ])
                ], className="mb-4")
            ], width=12),
        ]),
        dbc.Row([

            htm.Div([
                cardSets.renderGpuSettings()
                if conf.device.type in ['cuda', 'mps'] else
                cardSets.renderCpuSettings()
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Execute: Process Assets",
                    id=K.btnDoVec,
                    color="primary",
                    size="lg",
                    className="w-100",
                    disabled=True,
                ),
            ], width=6),

            dbc.Col([
                dbc.Button(
                    "Clear All Vectors",
                    id=K.btnClear,
                    color="danger",
                    size="lg",
                    className="w-100",
                    disabled=True,
                ),
            ], width=6),
        ], className="mb-4"),
        #====== top end =========================================================
    ], [
        #====== bottom start=====================================================

        #====== bottom end ======================================================
    ])



#========================================================================
# Page Status Management - Unified callback for button states
#========================================================================
@cbk(
    [
        out(K.btnDoVec, "children"),
        out(K.btnDoVec, "disabled"),
        out(K.btnClear, "disabled"),
        out(K.selectQ, "disabled"),
    ],
    [
        inp(ks.sto.cnt, "data"),
        inp(ks.sto.tsk, "data"),
    ],
    prevent_initial_call=False
)
def vec_UpdateStatus(dta_cnt, dta_tsk):
    cnt = models.Cnt.fromDic(dta_cnt) if dta_cnt else models.Cnt()
    tsk = models.Tsk.fromDic(dta_tsk) if dta_tsk else models.Tsk()

    hasPics = cnt.ass > 0
    hasVecs = cnt.vec > 0
    cntNeedVec = cnt.ass - cnt.vec
    isTskRunning = tsk.id is not None

    # Default values
    btnTxt = "Execute - Process Assets"
    disBtnRun = True
    disBtnClr = True
    disSelect = False

    lg.info(f"[vec] ass[{cnt.ass}] vec[{cnt.vec}] needVec[{cntNeedVec}] tskRunning[{isTskRunning}]")

    if isTskRunning:
        # Task is running
        btnTxt = "Task in progress.."
        disBtnRun = True
        disBtnClr = True
        disSelect = True
    elif hasVecs and cntNeedVec <= 0:
        # All assets vectorized
        btnTxt = "Vectors Complete"
        disBtnRun = True
        disBtnClr = False
        disSelect = True
    elif hasPics:
        # Has assets, some need vectorization
        if cntNeedVec > 0:
            btnTxt = f"Process Assets( {cntNeedVec} )"
            disBtnRun = False
        else:
            btnTxt = "Vectors Complete"
            disBtnRun = True
        disBtnClr = False if hasVecs else True
        disSelect = cntNeedVec <= 0
    else:
        # No assets
        btnTxt = "Please Get Assets First"
        disBtnRun = True
        disBtnClr = True
        disSelect = False

    return btnTxt, disBtnRun, disBtnClr, disSelect

#------------------------------------------------------------------------
#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.mdl, "data", allow_duplicate=True),
        out(ks.sto.nfy, "data", allow_duplicate=True),
        out(ks.sto.now, "data", allow_duplicate=True),
    ],
    [
        inp(K.btnDoVec, "n_clicks"),
        inp(K.btnClear, "n_clicks"),
    ],
    [
        ste(K.selectQ, "value"),
        ste(ks.sto.now, "data"),
        ste(ks.sto.cnt, "data"),
        ste(ks.sto.mdl, "data"),
        ste(ks.sto.tsk, "data"),
        ste(ks.sto.nfy, "data"),
    ],
    prevent_initial_call=True
)
def vec_RunModal(nclk_proc, nclk_clear, photoQ, dta_now, dta_cnt, dta_mdl, dta_tsk, dta_nfy):
    if not nclk_proc and not nclk_clear: return noUpd.by(3)

    trgId = getTrgId()
    if trgId == ks.sto.tsk and not dta_tsk.get('id'): return noUpd.by(3)

    tsk = models.Tsk.fromDic(dta_tsk)
    if tsk.id: return noUpd.by(3)

    now = models.Now.fromDic(dta_now)
    cnt = models.Cnt.fromDic(dta_cnt)
    mdl = models.Mdl.fromDic(dta_mdl)
    nfy = models.Nfy.fromDic(dta_nfy)

    lg.info(f"[vec] trig[{trgId}] clk[{nclk_proc}/{nclk_clear}] tsk[{tsk}]")

    if trgId == K.btnDoVec:
        if cnt.ass <= 0:
            nfy.error("No asset data to process")
        else:
            mdl.id = ks.pg.vector
            mdl.cmd = ks.cmd.vec.toVec
            mdl.msg = f"Begin processing photos[{cnt.ass - cnt.vec}] with quality[{photoQ}] ?"

            db.dto.photoQ = photoQ

    elif trgId == K.btnClear:
        if cnt.vec <= 0:
            nfy.error("No vector data to clear")
        else:
            mdl.id = ks.pg.vector
            mdl.cmd = ks.cmd.vec.clear
            mdl.msg = [
                "Are you sure you want to clear all vectors?"
            ]

    return mdl.toDict(), nfy.toDict(), now.toDict()


#========================================================================
# task acts
#========================================================================
import imgs
from mod.models import IFnProg

def vec_ToVec(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt
    msg = "[vec] Processing successful"

    try:
        photoQ = db.dto.photoQ

        doReport(1, f"Initializing with photoQ[{photoQ}]")

        # Check for cancellation early
        if sto.isCancelled():
            msg = "Task was cancelled before processing"
            nfy.info(msg)
            return sto, msg

        assets = db.pics.getAllNonVector()
        doReport(5, f"Getting asset data count[{len(assets)}]")

        if not assets or len(assets) == 0:
            msg = "No assets to process"
            nfy.error(msg)
            return sto, msg

        # Check for cancellation after getting assets
        if sto.isCancelled():
            msg = "Task was cancelled during initialization"
            nfy.info(msg)
            return sto, msg

        cntAll = len(assets)
        doReport(8, f"Found [ {cntAll} ] starting processing")

        # Pass the cancel checker to processVectors
        rst = imgs.processVectors(assets, photoQ, onUpdate=doReport, isCancelled=sto.isCancelled)

        # Check for cancellation after processing
        if sto.isCancelled():
            msg = f"Processing cancelled: completed[ {rst.done} ] error[ {rst.erro} ]"
            nfy.info(msg)
            return sto, msg

        cnt.vec = db.vecs.count()

        msg = f"Completed: total[ {rst.all} ] done[ {rst.done} ] Skip[ {rst.skip} ]"
        if rst.erro: msg += f" Error[ {rst.erro}]"

        nfy.success(msg)

        return sto, msg

    except Exception as e:
        if sto.isCancelled():
            msg = "Task was cancelled"
            nfy.info(msg)
            return sto, msg
        else:
            msg = f"Asset processing failed: {str(e)}"
            nfy.error(msg)
            raise RuntimeError(msg)


def vec_Clear(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt
    msg = "[AssetVec] Clearing successful"

    try:
        doReport(10, "Preparing to clear all Vectors")

        if cnt.vec <= 0:
            msg = "No vector data to clear"
            nfy.warn(msg)
            return sto, msg

        doReport(30, "Clearing Vectors...")

        count = db.vecs.count()
        if count >= 0:
            db.vecs.cleanAll()
            db.pics.clearAllVectored()

        doReport(90, f"Cleared {count} vector records")

        cnt.vec = 0

        msg = f"Successfully cleared all photo vector data ({count} records)"
        nfy.success(msg)

        doReport(100, "Clearing complete")
        return sto, msg

    except Exception as e:
        msg = f"Failed to clear vectors: {str(e)}"
        nfy.error(msg)
        raise RuntimeError(msg)

#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.vec.toVec] = vec_ToVec
mapFns[ks.cmd.vec.clear] = vec_Clear
