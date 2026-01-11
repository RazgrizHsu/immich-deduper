from dsh import dash, htm, dcc, cbk, dbc, inp, out, ste, getTrgId, noUpd
from util import log
from mod import models, tskSvc
import db
from conf import ks

lg = log.get(__name__)

dash.register_page(
    __name__,
    path=f'/{ks.pg.fetch}',
    title=f"{ks.title}: " + ks.pg.fetch.name,
)

class k:
    selectUsr = "fetch-usr-select"
    btnFetch = "fetch-btn-assets"
    btnClean = "fetch-btn-clear"
    btnReset = "fetch-btn-reset"

    initFetch = "fetch-init"


opts = []  #[{"label": "All Users", "value": ""}] # current no support

#========================================================================
def layout():
    import ui
    return ui.renderBody([
        #====== top start =======================================================

        htm.Div([
            htm.H3(f"{ks.pg.fetch.name}"),
            htm.Small(f"{ks.pg.fetch.desc}", className="text-muted")
        ], className="body-header"),

        dbc.Card([
            dbc.CardHeader("Settings"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Select User"),
                        dbc.Select( id=k.selectUsr, options=[], placeholder="Select user."),
                    ], width=12),
                ],
                    className="mb-2"
                ),
                htm.Ul([
                    htm.Li("Assets that already exist locally will be skipped"),
                    htm.Li("Assets without generated thumbnails in Immich will also be skipped"),
                    htm.Li("Updates may sync: paths, EXIF data, favorite/archive status. Re-fetch if these change in remote"),
                    htm.Li([
                        htm.Strong("Sync deletion: "),
                        "Local assets that are no longer in 'active' status in Immich (e.g., moved to trash) will be automatically removed along with their vectors"
                    ]),
                ]),
            ])
        ], className="mb-4"),


        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "loading..",
                    id=k.btnFetch,
                    color="primary",
                    size="lg",
                    className="w-100",
                    disabled=True,
                ),

            ], width=5),

            dbc.Col([
                dbc.Button(
                    "loading..",
                    id=k.btnClean,
                    color="danger",
                    size="lg",
                    className="w-100",
                ),
            ], width=4),
            dbc.Col([
                htm.Div("Please proceed with caution", className="txt-sm"),
                dbc.Button(
                    "Reset All local data",
                    id=k.btnReset,
                    size="sm",
                    color="danger",
                    className="w-100",
                ),
            ], width=3),

        ], className="mb-4"),
        #====== top end =========================================================
    ], [
        #====== bottom start=====================================================


        # *[htm.Div(f"這是第 {i + 1} 個 div") for i in range(10)],

        dcc.Store(id=k.initFetch),
        #====== bottom end ======================================================
    ])


#========================================================================
dis_show = {"display": "block"}
dis_hide = {"display": "none"}

#========================================================================
@cbk(
    [
        out(k.selectUsr, "options"),
        out(k.selectUsr, "value"),
    ],
    inp(k.initFetch, "data"),
)
def fth_Init(dta_pi):
    lg.info(f"[fth:init] select usrId[{db.dto.usrId}]")

    opts = []
    usrs = db.psql.fetchUsers()
    if usrs and len(usrs) > 0:
        # Check if stored usrId exists in fetched users
        if db.dto.usrId:
            validUsrIds = {str(usr.id) for usr in usrs}
            if db.dto.usrId not in validUsrIds:
                lg.warn(f"[fth:init] stored usrId[{db.dto.usrId}] not found in database, clearing...")
                db.dto.usrId = None

        for usr in usrs:
            opts.append({"label": usr.name, "value": str(usr.id)})

    return opts, db.dto.usrId


#------------------------------------------------------------------------
# Update button text and enabled status based on selected data source and user
#------------------------------------------------------------------------
@cbk(
    [
        out(k.btnFetch, "children"),
        out(k.btnFetch, "disabled"),
        out(k.btnClean, "children"),
        out(k.btnClean, "disabled"),
        out(ks.sto.nfy, "data", allow_duplicate=True)
    ],
    [
        inp(k.selectUsr, "value"),
        inp(ks.sto.cnt, "data"),
    ],
    ste(ks.sto.tsk, "data"),
    ste(ks.sto.nfy, "data"),
    prevent_initial_call=True
)
def fth_Status(usrId, dta_cnt, dta_tsk, dta_nfy):
    tsk = models.Tsk.fromDic(dta_tsk)
    cnt = models.Cnt.fromDic(dta_cnt)
    nfy = models.Nfy.fromDic(dta_nfy)

    # hasData = cnt.vec > 0 or cnt.ass > 0

    isTasking = tsk.id is not None

    disBtnRun = isTasking
    disBtnClr = isTasking

    txtBtn = f"Fetch: Get Assets"
    txtClr = f"Clean Data"

    if usrId and usrId != db.dto.usrId:
        usr = db.psql.fetchUser(usrId)
        if usr:
            db.dto.usrId = usrId
            nfy.info(f"Switched user: {usr.name}")
        else:
            usrId = db.dto.usrId = None

    if isTasking:
        disBtnRun = disBtnClr = True
        txtBtn = "Task in progress..."

    if not db.dto.usrId:
        disBtnRun = disBtnClr = True
        txtBtn = "Please select user"
        nfy.info(txtBtn)

    elif usrId == "":
        disBtnRun = disBtnClr = True
        txtBtn = "Please select user"
        txtClr = "---"
    else:
        if not db.dto.usrId:
            disBtnRun = disBtnClr = True
            txtBtn = "--No users--"
        else:
            usr = db.psql.fetchUser(db.dto.usrId)
            cntRemote = db.psql.count(db.dto.usrId)
            cntLocal = db.pics.count(db.dto.usrId)

            if cntLocal <= 0:
                disBtnClr = True

            disBtnRun = cntRemote <= cntLocal or cntRemote == 0

            if usr:
                txtBtn = f"Fetch: {usr.name} ({cntRemote})"
                txtClr = f"Clear local: {usr.name} ({cntLocal})"
            else:
                txtBtn = "--No user--"
                txtClr = "--No user--"

    lg.info(f"[fth:status] cnt: {cnt}")

    return txtBtn, disBtnRun, txtClr, disBtnClr, nfy.toDict()

#------------------------------------------------------------------------
#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.mdl, "data", allow_duplicate=True),
        out(ks.sto.nfy, "data", allow_duplicate=True)
    ],
    [
        inp(k.btnFetch, "n_clicks"),
        inp(k.btnClean, "n_clicks"),
        inp(k.btnReset, "n_clicks"),
    ],
    [
        ste(k.selectUsr, "value"),
        ste(ks.sto.now, "data"),
        ste(ks.sto.mdl, "data"),
        ste(ks.sto.tsk, "data"),
        ste(ks.sto.nfy, "data"),
    ],
    prevent_initial_call=True
)
def fth_RunModal(clk_feh, clk_clr, clk_rst, usrId, dta_now, dta_mdl, dta_tsk, dta_nfy):
    if not clk_feh and not clk_clr and not clk_rst: return noUpd.by(2)

    now = models.Now.fromDic(dta_now)
    mdl = models.Mdl.fromDic(dta_mdl)
    tsk = models.Tsk.fromDic(dta_tsk)
    nfy = models.Nfy.fromDic(dta_nfy)

    if tsk.id: return noUpd.by(2)
    trgSrc = getTrgId()

    if trgSrc == k.btnReset:
        mdl.id = ks.pg.fetch
        mdl.cmd = ks.cmd.fetch.reset
        mdl.msg = [
            htm.Div([htm.B('Warning:'), ' Reset all local data'], className="p-5")
        ]
    elif trgSrc == k.btnClean:
        if not db.dto.usrId:
            nfy.warn("not select user..")
            mdl.reset()
        else:
            usr = db.psql.fetchUser(db.dto.usrId)
            cnt = db.pics.count(db.dto.usrId)

            if not usr:
                nfy.warn( f"No User Id[{ db.dto.usrId }]" )
            else:
                mdl.id = ks.pg.fetch
                mdl.cmd = ks.cmd.fetch.clear
                mdl.msg = f'Start clearing user[ {usr.name} ] assets[ {cnt} ]'

    elif trgSrc == k.btnFetch:
        if not db.dto.usrId:
            nfy.warn("not select user..")
            mdl.reset()
        else:
            cnt = db.psql.count(db.dto.usrId)
            usr = db.psql.fetchUser(db.dto.usrId)

            if not usr:
                nfy.warn( f"No User Id[{ db.dto.usrId }]" )
            else:
                mdl.id = ks.pg.fetch
                mdl.cmd = ks.cmd.fetch.asset
                mdl.msg = f"Start getting assets[ {cnt} ] for user[ {usr.name} ] ?"

    return mdl.toDict(), nfy.toDict()


#------------------------------------------------------------------------
#------------------------------------------------------------------------


#========================================================================
# task acts
#========================================================================
from mod import mapFns
from mod.models import IFnProg

#------------------------------------------------------------------------
def onFetchAssets(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt

    try:
        # todo: add support for all users?

        if not db.dto.usrId:
            raise RuntimeError( f"No UserId" )

        try:
            db.psql.chk()
        except Exception as e:
            msg = f"Error: Cannot connect to PostgreSQL database: {str(e)}"
            nfy.error(msg)
            return sto, msg

        usr = db.psql.fetchUser(db.dto.usrId)

        if not usr:
            msg = f"Error: User not found"
            nfy.error(msg)
            return sto, msg

        doReport(5, f"Starting to fetch assets for {usr.name} from PostgreSQL")

        cntAll = db.psql.count(usr.id)
        if cntAll <= 0:
            msg = f"No assets found for {usr.name}"
            nfy.info(msg)
            return sto, msg

        doReport(10, f"Found {cntAll} photos, starting to fetch assets")

        try:
            assets = db.psql.fetchAssets(usr, onUpdate=doReport)

        except Exception as e:
            msg = f"Error fetching assets for {usr.name}, {str(e)}"
            nfy.error(msg)
            return sto, msg

        if not assets or len(assets) == 0:
            msg = f"No assets retrieved for {usr.name}"
            nfy.error(msg)
            return sto, msg

        doReport(50, f"Retrieved {len(assets)} photos, starting to save to local database")

        cntFetch = len(assets)
        cntNew = 0
        cntUpd = 0
        cntSkip = 0

        # updateIds = []
        # def onUpdAss( ass:models.Asset ):
        #     nonlocal updateIds
        #     updateIds.append( ass.id )

        with db.pics.mkConn() as conn:
            c = conn.cursor()
            for idx, asset in enumerate(assets):
                if idx % 10 == 0:
                    prog = 50 + int((idx / len(assets)) * 40)
                    doReport(prog, f"Saving photo {idx}/{len(assets)}")

                rst = db.pics.saveBy(asset, c)
                if rst == 1: cntNew += 1
                elif rst == 2: cntUpd += 1
                else: cntSkip += 1

            conn.commit()

        # Sync deletion: Remove local assets that no longer exist in remote (status != 'active')
        doReport(90, f"Syncing with remote: checking for deleted assets")

        # Get all local asset IDs for this user
        localAssets = db.pics.getAllByUsrId(usr.id)
        if localAssets and len(localAssets) > 0:
            localIds = {str(asset.id) for asset in localAssets}
            remoteIds = {str(asset['id']) for asset in assets}

            # Find assets that exist locally but not in remote active assets
            toDeleteIds = list(localIds - remoteIds)

            if toDeleteIds:
                doReport(92, f"Found {len(toDeleteIds)} assets to remove (no longer active in Immich)")

                # Get autoIds before deleting
                localMap = {str(a.id): a.autoId for a in localAssets}
                toDelAids = [localMap[aid] for aid in toDeleteIds if aid in localMap]

                # Delete from local database
                with db.pics.mkConn() as conn:
                    c = conn.cursor()
                    for assetId in toDeleteIds:
                        c.execute("DELETE FROM assets WHERE id = ?", (assetId,))
                    conn.commit()

                # Delete vectors
                try:
                    db.vecs.deleteBy(toDelAids)
                    doReport(95, f"Removed {len(toDeleteIds)} assets and their vectors")
                except Exception as e:
                    lg.error(f"Failed to delete vectors for removed assets: {str(e)}")

                cntDeleted = len(toDeleteIds)
            else:
                cntDeleted = 0
                doReport(95, "No assets need to be removed")
        else:
            cntDeleted = 0

        cnt.ass = db.pics.count()

        doReport(100, f"Completed: {cntNew} new, {cntUpd} updated, {cntSkip} unchanged, {cntDeleted} removed")

        cntSkipped = cntAll - cntFetch
        msg = f"success, user[ {usr.name} ] total[ {cntAll} ] fetched[ {cntFetch} ] skipped[ {cntSkipped} ] - new[ {cntNew} ] updated[ {cntUpd} ] unchanged[ {cntSkip} ] removed[ {cntDeleted} ]"
        nfy.info(msg)

        return sto, msg

    except Exception as e:
        msg = f"Failed fetching assets: {str(e)}"
        nfy.error(msg)

        raise RuntimeError(msg)

#------------------------------------------------------------------------
def onFetchClear(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt

    msg = "[Assets:Clear] Successfully cleared all assets"
    import db

    try:
        db.psql.chk()
    except Exception as e:
        msg = f"Error: Cannot connect to PostgreSQL database: {str(e)}"
        nfy.error(msg)
        return sto, msg

    try:
        if not db.dto.usrId:
            raise RuntimeError( "NoUserId" )

        usr = db.psql.fetchUser(db.dto.usrId)
        if not usr:
            msg = f"Error: User not found"
            nfy.error(msg)
            return sto, msg

        doReport(10, f"Starting clear assets for {usr.name}")

        assets = db.pics.getAllByUsrId(db.dto.usrId)
        if not assets or len(assets) == 0:
            msg = f"No assets found for {usr.name}"
            return sto, msg

        assIds = [a.autoId for a in assets]
        #------------------------------------
        db.pics.clearBy(db.dto.usrId)

        db.vecs.deleteBy(assIds)

        cnt.refreshFromDB()

        return sto, msg
    except Exception as e:
        msg = f"Failed to clear user data: {str(e)}"
        nfy.error(msg)
        raise RuntimeError(msg)

#------------------------------------------------------------------------
def onFetchReset(doReport: IFnProg, sto: models.ITaskStore):
    nfy, now, cnt = sto.nfy, sto.now, sto.cnt

    msg = "[Assets:Reset] Successfully"
    import db

    try:
        doReport(10, f"Starting reset assets")
        db.resetAllData()

        cnt.refreshFromDB()

        return sto, msg
    except Exception as e:
        msg = f"Failed to clear all data: {str(e)}"
        nfy.error(msg)
        raise RuntimeError(msg)


#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.fetch.asset] = onFetchAssets
mapFns[ks.cmd.fetch.clear] = onFetchClear
mapFns[ks.cmd.fetch.reset] = onFetchReset
