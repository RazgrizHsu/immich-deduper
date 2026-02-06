import json
from dash.dependencies import ALL
from dsh import htm, dcc, dbc, inp, out, ste, cbk, ccbk, cbkFn, noUpd, ctx, toOpts

from dto import *
from util import log


lg = log.get(__name__)

from conf import ks, co
import db
from mod import models


class k:
    threshold = "thresholds"
    autoNext = "autoNext"
    showGridInfo = "showGridInfo"
    simRtree = "simRtree"
    simMaxItems = "simMaxItems"
    pathFilter = "pathFilter"

    muodOn = "muodOn"
    muodMx = "muodMx"
    gpskEqD = "gpskEqD"
    gpskEqW = "gpskEqW"
    gpskEqH = "gpskEqH"
    gpskEqFsz = "gpskEqFsz"

    gpuAutoMode = "gpuAutoMode"
    gpuBatchSize = "gpuBatchSize"

    cpuAutoMode = "cpuAutoMode"
    cpuWorkers = "cpuWorkers"

    libPathsData = "libPathsData"
    libPathsContainer = "libPathsContainer"

    immichPath = "immichPath"
    immichThumb = "immichThumb"

    @staticmethod
    def id(name): return {"type": "sets", "id": f"{name}"}

    @staticmethod
    def libPathId(idx): return {"type": "libPath", "idx": idx}

    @staticmethod
    def libPathChk(idx): return {"type": "libPathChk", "idx": idx}

    @staticmethod
    def ausl(field): return {"type": "ausl", "field": field}

    @staticmethod
    def mrg(field): return {"type": "mrg", "field": field}

    @staticmethod
    def excl(field): return {"type": "excl", "field": field}


optThresholdMin = 0.5
optThresholdMarks = {"0.5":0.5, "0.6":0.6, "0.7": 0.7, "0.8": 0.8, "0.9": 0.9, "1": 1}

optMaxDepths = []
for i in range(6): optMaxDepths.append({"label": f"{i}", "value": i})

optMaxItems = []
for i in [10, 50, 100, 200, 300, 500, 1000]: optMaxItems.append({"label": f"{i}", "value": i})

optMaxGroups = []
for i in [2, 5, 10, 20, 25, 50, 100]: optMaxGroups.append({"label": f"{i}", "value": i})

optWeights = []
for i in range(5): optWeights.append({"label": f"{i}", "value": i})

def _getUsrOpts():
    opts = [{"label": "--", "value": ""}]
    try:
        usrs = db.psql.fetchUsers()
        if usrs:
            for usr in usrs: opts.append({"label": usr.name or usr.email or usr.id[:8], "value": str(usr.id)})
    except: pass
    return opts


optExclLess = [{"label": "--", "value": 0}]
for i in range(1,6): optExclLess.append({"label": f" < {i}", "value": i})

optExclOver = [{"label": "--", "value": 0}]
for i in [10,20,30,50,100]: optExclOver.append({"label": f" > {i}", "value": i})

optGpuBatch = {}
for i in [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]: optGpuBatch[str(i)] = i

optCpuWorkers = {}
import multiprocessing
cpuCnt = multiprocessing.cpu_count()
if cpuCnt is None: cpuCnt = multiprocessing.cpu_count()
for i in range(1, min(cpuCnt + 1, 17)): optCpuWorkers[str(i)] = i

def renderThreshold():
    return dbc.Card([
        dbc.CardHeader(["Threshold Min",htm.Small("sets minimum similarity for matching")]),
        dbc.CardBody([
            htm.Div([
                htm.Div([
                    dcc.Slider(
                        id=k.id(k.threshold), min=optThresholdMin, max=1, step=0.01, marks=optThresholdMarks, #type: ignore
                        value=db.dto.thMin, included=False,
                        tooltip={"placement": "top", "always_visible": True, "style": {"padding": "0 1px 0 1px", "fontSize": "11px"},},
                    ),
                ], className=""),
                htm.Ul([])
            ], className="irow mb-0"),
        ])
    ], className="ifns mb-1")

def renderMerge():
    m = db.dto.mrg
    dis = not m.on
    return dbc.Card([
        dbc.CardHeader([
            "Metadata Merge ",
            htm.Small(["from deleted to kept photos",htm.Span("BETA", className="tag yellow text-dark ms-1 no")]),
        ]),
        dbc.CardBody([
            htm.Div([

                htm.Div([
                    dbc.Checkbox(id=k.mrg("on"), label="Enable", value=m.on),
                    htm.Div([
                        htm.Div([htm.B("WARN!")," Writes directly to Immich"], className="text-warning"),
                        htm.Div(["Failed when original path can't access"], className="text-muted"),
                    ]),
                ], className="icbxs single"),


                htm.Hr(),

                htm.Div([
                    dbc.Checkbox(id=k.mrg("albums"), label="Albums", value=m.albums, disabled=dis),
                    dbc.Checkbox(id=k.mrg("favs"), label="Favorites", value=m.favs, disabled=dis),
                    dbc.Checkbox(id=k.mrg("tags"), label="Tags", value=m.tags, disabled=dis),
                    dbc.Checkbox(id=k.mrg("rating"), label="Rating", value=m.rating, disabled=dis),
                    dbc.Checkbox(id=k.mrg("desc"), label="Description", value=m.desc, disabled=dis),
                    dbc.Checkbox(id=k.mrg("loc"), label="Location", value=m.loc, disabled=dis),
                    dbc.Checkbox(id=k.mrg("vis"), label="Visibility", value=m.vis, disabled=dis),
                ], className="icbxs"),
            ], className="mb-1 igrid txt-sm"),
        ])
    ], className="ifns mb-1")


def renderAutoSelect():
    a = db.dto.ausl
    dis = not a.on
    return dbc.Card([
        dbc.CardHeader([htm.Span("Auto Selection"),htm.Small(["selects top point in group",htm.Br(),"auto-updates on change"])]),
        dbc.CardBody([
            htm.Div([
                # Main enable switch
                htm.Div([
                    dbc.Checkbox(id=k.ausl("on"), label="Enable", value=a.on),
                    htm.Div([
                        htm.Span([htm.B("Points: "),"0=Ignore, 1=Low, 2=High priority"], className="text-muted")
                    ]),
                ], className="icbxs single"),

                dbc.Checkbox(id=k.ausl("skipLow"), label="Skip has sim(<0.96) group", value=a.skipLow, disabled=dis),
                dbc.Checkbox(id=k.ausl("allLive"), label="All LivePhotos (ignore criteria)", value=a.allLive, disabled=dis), htm.Br(),

                htm.Hr(),

                htm.Div([
                    htm.Span(htm.Span("DateTime", className="tag txt-smx me-1")),
                    htm.Label("Earlier", className="me-2"),
                    dbc.Select(id=k.ausl("earlier"), options=toOpts(optWeights), value=a.earlier, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Later", className="me-2"),
                    dbc.Select(id=k.ausl("later"), options=toOpts(optWeights), value=a.later, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Exif", className="tag txt-smx me-1")),
                    htm.Label("Richer", className="me-2"),
                    dbc.Select(id=k.ausl("exRich"), options=toOpts(optWeights), value=a.exRich, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Poorer", className="me-2"),
                    dbc.Select(id=k.ausl("exPoor"), options=toOpts(optWeights), value=a.exPoor, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Name Length", className="tag txt-smx me-1")),
                    htm.Label("Longer", className="me-2"),
                    dbc.Select(id=k.ausl("namLon"), options=toOpts(optWeights), value=a.namLon, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Shorter", className="me-2"),
                    dbc.Select(id=k.ausl("namSht"), options=toOpts(optWeights), value=a.namSht, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("FileSize", className="tag txt-smx me-1")),
                    htm.Label("Bigger", className="me-2"),
                    dbc.Select(id=k.ausl("ofsBig"), options=toOpts(optWeights), value=a.ofsBig, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Smaller", className="me-2"),
                    dbc.Select(id=k.ausl("ofsSml"), options=toOpts(optWeights), value=a.ofsSml, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Dimensions", className="tag txt-smx me-1")),
                    htm.Label("Bigger", className="me-2"),
                    dbc.Select(id=k.ausl("dimBig"), options=toOpts(optWeights), value=a.dimBig, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Smaller", className="me-2"),
                    dbc.Select(id=k.ausl("dimSml"), options=toOpts(optWeights), value=a.dimSml, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("File Type", className="tag txt-smx me-1")),
                    htm.Label("Jpg", className="me-2"),
                    dbc.Select(id=k.ausl("typJpg"), options=toOpts(optWeights), value=a.typJpg, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Png", className="me-2"),
                    dbc.Select(id=k.ausl("typPng"), options=toOpts(optWeights), value=a.typPng, disabled=dis, size="sm", className="me-1"),
                    htm.Label("Heic", className="me-2"),
                    dbc.Select(id=k.ausl("typHeic"), options=toOpts(optWeights), value=a.typHeic, disabled=dis, size="sm"),
                ], className="icriteria wrap"),

                htm.Div([
                    htm.Span(htm.Span("Immich", className="tag txt-smx me-1")),
                    htm.Label("Favorited", className="me-2"),
                    dbc.Select(id=k.ausl("fav"), options=toOpts(optWeights), value=a.fav, disabled=dis, size="sm", className="me-1"),
                    htm.Label("In Album", className="me-2"),
                    dbc.Select(id=k.ausl("inAlb"), options=toOpts(optWeights), value=a.inAlb, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("User", className="tag txt-smx me-1")),
                    htm.Label("name", className="me-2"),
                    dbc.Select(id=k.ausl("usrPri"), options=toOpts(_getUsrOpts()), value=a.usr.k, disabled=dis, size="sm", className="me-1", style={"minWidth": "60px"}),
                    htm.Label("Weight", className="me-2"),
                    dbc.Select(id=k.ausl("usrWgt"), options=toOpts(optWeights), value=a.usr.v, disabled=dis, size="sm"),
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Path", className="tag txt-smx me-1")),
                    htm.Label("Contains", className="me-2"),
                    dbc.Input(id=k.ausl("pthVal"), value=a.pth.k, disabled=dis, className="me-1 txt-smx", style={"maxWidth": "80%"}, placeholder="e.g. /library/clean", debounce=1000),
                    htm.Label("Weight", className="me-2"),
                    dbc.Select(id=k.ausl("pthWgt"), options=toOpts(optWeights), value=a.pth.v, disabled=dis, size="sm"),
                ], className="icriteria"),

            ], className="mb-2 igrid txt-sm"),
        ])
    ], className="ifns mb-0")


def renderCard():
    return dbc.Card([
        dbc.CardHeader("Search Settings"),
        dbc.CardBody([
            htm.Div([
                htm.Label("Find Settings", className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.autoNext), label="Auto Find Next", value=db.dto.autoNext),
                    dbc.Checkbox(id=k.id(k.showGridInfo), label="Show Grid Info", value=db.dto.showGridInfo),
                    htm.Div(id={"type": "dummy", "id": "grid-info"}, style={"display": "none"}),

                    htm.Div([
                        htm.Label("Max Items: "),
                        dbc.Select(id=k.id(k.simMaxItems), options=toOpts(optMaxItems), value=db.dto.rtreeMax, className="")
                    ]),
                ], className="icbxs"),
                htm.Ul([
                    htm.Li([htm.B("Max Items: "), "Max images to process in similarity search to prevent UI slowdown"])
                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Related Tree",
                    htm.Span("Expand similar-tree to include relateds. Keep/Delete affects all displayed images", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.simRtree), label="Related Tree", value=db.dto.rtree),

                ], className="icbxs"),
                htm.Ul([

                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Multi Mode",
                    htm.Span("Find multiple groups of similar photos (mutually exclusive with Related Tree)", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.muodOn), label="Enable", value=db.dto.muod.on),

                    htm.Div([
                        htm.Label("Max Groups: "),
                        dbc.Select(id=k.id(k.muodMx), options=toOpts(optMaxGroups), value=db.dto.muod.sz, className="", disabled=True)
                    ]),
                ], className="icbxs"),
                htm.Ul([
                    htm.Li([htm.B("Max Groups: "), "Maximum number of groups to return when grouping is enabled"]),
                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Group Conditions",
                    htm.Span("Filter groups where all photos must match these criteria", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.gpskEqD), label="Same Date", value=db.dto.gpsk.eqDt),
                    dbc.Checkbox(id=k.id(k.gpskEqW), label="Same Width", value=db.dto.gpsk.eqW),
                    dbc.Checkbox(id=k.id(k.gpskEqH), label="Same Height", value=db.dto.gpsk.eqH),
                    dbc.Checkbox(id=k.id(k.gpskEqFsz), label="Same File Size", value=db.dto.gpsk.eqFsz),
                ], className="icbxs"),
                htm.Ul([
                    htm.Li("Groups not matching conditions are auto-resolved")
                ])
            ], className="irow"),

            htm.Div([
                htm.Label("Path Filter", className="txt-sm"),
                htm.Div([
                    htm.Label("Contains: "),
                    dbc.Input(id=k.id(k.pathFilter), maxlength=200, placeholder='e.g. /store/user/folder', value=db.dto.pathFilter, className="txt-sm", style={"maxWidth": "300px"})
                ], className="icbxs"),
                htm.Ul([
                    htm.Li("Only show groups with at least one asset matching this path pattern"),
                    htm.Li("Groups without matching paths are auto-resolved")
                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Exclude Settings",
                    htm.Span("", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.excl("on"), label="Enable", value=db.dto.excl.on, className="txt-sm"),

                    htm.Div([
                        htm.Label("SimilarLess: ", className="txt-sm"),
                        dbc.Select(id=k.excl("fndLes"), options=toOpts(optExclLess), value=db.dto.excl.fndLes, className="txt-smx", disabled=not db.dto.excl.on, style={"maxWidth": "30px"})
                    ]),

                    htm.Div([
                        htm.Label("SimilarOver: ", className="txt-sm"),
                        dbc.Select(id=k.excl("fndOvr"), options=toOpts(optExclOver), value=db.dto.excl.fndOvr, className="txt-smx", disabled=not db.dto.excl.on, style={"maxWidth": "30px"})
                    ]),

                    htm.Div([
                        htm.Label("NameFilter", className="txt-sm"),
                        dbc.Input(id=k.excl("filNam"), maxlength=70, placeholder='separate by ","', value=db.dto.excl.filNam, disabled=not db.dto.excl.on, className="txt-sm", style={"maxWidth": "80px"})
                    ]),

                ], className="icbxs"),
                htm.Ul([
                    htm.Li([
                        htm.B("Similar Less: "),
                        "Skip groups with fewer than N similar photos (excluding the main one)",
                        htm.Ul([
                            htm.Li("Example: '< 2' skips groups with only 0 or 1 similar photo (needs at least 3 total)")
                        ])
                    ]),

                    htm.Li([
                        htm.B("NameFilter: "),
                        "Exclude files by filename keywords or extensions",
                        htm.Ul([
                            htm.Li("Extension format: .png,.gif,.dng (won’t be main or in results)"),
                            htm.Li("Filename keywords: IMG_,DSC,screenshot (skip if name contains any of these)"),
                            htm.Li("Mixed: .png,IMG_,screenshot (combine both types)")
                        ])
                    ])
                ])
            ], className="irow"),
        ])
    ], className="ifns mb-0")


@cbk(
    [
        out(ks.sto.now, "data", allow_duplicate=True),
        out(k.id(k.muodMx), "disabled"),
    ],
    inp(k.id(k.threshold), "value"),
    inp(k.id(k.autoNext), "value"),
    inp(k.id(k.showGridInfo), "value"),
    inp(k.id(k.simRtree), "value"),
    inp(k.id(k.simMaxItems), "value"),
    inp(k.id(k.pathFilter), "value"),
    inp(k.id(k.muodOn), "value"),
    inp(k.id(k.muodMx), "value"),
    inp(k.id(k.gpskEqD), "value"),
    inp(k.id(k.gpskEqW), "value"),
    inp(k.id(k.gpskEqH), "value"),
    inp(k.id(k.gpskEqFsz), "value"),
    ste(ks.sto.now, "data"),
    prevent_initial_call=True
)
def settings_OnUpd(th, auNxt, shGdInfo, rtree,  maxItems, pathFilter, muodOn,muodMxGs, gDt, gW, gH, gFsz, dta_now):
    retNow = noUpd

    now = models.Now.fromDic(dta_now)

    db.dto.thMin = co.vad.float(th, 0.93, 0.50, 1.0)

    db.dto.autoNext = auNxt
    db.dto.rtreeMax = maxItems
    db.dto.pathFilter = pathFilter or ''

    db.dto.muod = Muod(muodOn, muodMxGs or 10)
    db.dto.gpsk = Gpsk(gDt,gW,gH,gFsz)

    maxGroupsDisabled = not muodOn

    def reloadAssets():
        nonlocal retNow, now
        lg.info(f"[sets:OnUpd] reload, rtree[{db.dto.rtree}] muodMode[{db.dto.muod.on}]")
        now.sim.assCur = db.pics.getSimAssets(now.sim.assAid, db.dto.rtree if not db.dto.muod.on else False)
        retNow = now

    if db.dto.showGridInfo != shGdInfo: db.dto.showGridInfo = shGdInfo

    if db.dto.rtree != rtree:
        db.dto.rtree = rtree
        if retNow == noUpd: reloadAssets()

    return [retNow, maxGroupsDisabled]


@cbk(
    [
        out({"type": "ausl", "field": ALL}, "disabled"),
        out(ks.sto.sets, "data", allow_duplicate=True),
    ],
    inp({"type": "ausl", "field": ALL}, "value"),
    prevent_initial_call=True
)
def ausl_OnUpd(values):
    from dtom import PairKv
    from dataclasses import asdict
    a = db.dto.ausl
    usrPri, usrWgt = None, None
    pthVal, pthWgt = None, None

    # ctx.inputs_list[0] 格式: [{'id': {'field': 'on', 'type': 'ausl'}, 'value': True}, ...]
    fields = []
    for item in ctx.inputs_list[0]:
        fld = item['id']['field']
        val = item['value']
        fields.append(fld)

        if fld == 'usrPri': usrPri = val
        elif fld == 'usrWgt': usrWgt = val
        elif fld == 'pthVal': pthVal = val
        elif fld == 'pthWgt': pthWgt = val
        else: setattr(a, fld, val)

    a.usr = PairKv(k=usrPri or '', v=usrWgt or 0)
    a.pth = PairKv(k=pthVal or '', v=pthWgt or 0)

    lg.info(f"[ausl:OnUpd] {a}")

    # on 開關永遠不 disable，其他根據 a.on 決定
    disabledStates = [False if f == 'on' else not a.on for f in fields]
    setsData = {'ausl': asdict(a.raw())}
    return disabledStates, setsData


@cbk(
    out({"type": "excl", "field": ALL}, "disabled"),
    inp({"type": "excl", "field": ALL}, "value"),
    prevent_initial_call=True
)
def excl_OnUpd(values):
    e = db.dto.excl

    fields = []
    for item in ctx.inputs_list[0]:
        fld = item['id']['field']
        val = item['value']
        fields.append(fld)
        setattr(e, fld, val)

    lg.info(f"[excl:OnUpd] {e}")
    return [False if f == 'on' else not e.on for f in fields]


def renderGpuSettings():
    return dbc.Card([
        dbc.CardHeader("GPU Performance"),
        dbc.CardBody([
            htm.Div([
                htm.Label("GPU Batch Processing", className="txt-sm"),
                htm.Div([

                    dbc.Checkbox(id=k.id(k.gpuAutoMode), label="Auto Batch Size", value=db.dto.gpuAutoMode),

                    htm.Div([
                        htm.Label("Batch Size: "),
                        dcc.Slider(
                            id=k.id(k.gpuBatchSize),
                            min=1, max=64, step=1,
                            value=db.dto.gpuBatchSize,
                            marks=optGpuBatch,
                            disabled=db.dto.gpuAutoMode,
                            tooltip={"placement": "top", "always_visible": True}
                        )
                    ], className="mt-2"),

                ]),
                htm.Ul([
                    htm.Li([htm.B("Auto Mode: "), "Automatically selects optimal batch size based on GPU memory"]),
                    htm.Li([htm.B("Manual Mode: "), "Manually adjust batch size. Larger values use more GPU memory but may be faster"]),
                    htm.Li([htm.B("Suggested: "), "8GB GPU use 8-12, 16GB+ GPU can use 16-32"])
                ])
            ], className="irow"),
        ])
    ], className="mb-2")


def renderCpuSettings():
    import multiprocessing
    cpuCnt = multiprocessing.cpu_count()
    if cpuCnt is None: cpuCnt = multiprocessing.cpu_count()
    return dbc.Card([
        dbc.CardHeader("CPU Performance"),
        dbc.CardBody([
            htm.Div([
                htm.Label("CPU Multi-Threading", className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.cpuAutoMode), label="Auto Workers", value=db.dto.cpuAutoMode),

                    htm.Div([
                        htm.Label("Worker Threads: "),
                        dcc.Slider(
                            id=k.id(k.cpuWorkers),
                            min=1, max=min(cpuCnt, 16), step=1,
                            value=db.dto.cpuWorkers,
                            marks=optCpuWorkers,
                            disabled=db.dto.cpuAutoMode,
                            tooltip={"placement": "top", "always_visible": True}
                        )
                    ], className="mt-2"),

                ]),
                htm.Ul([
                    htm.Li([htm.B("Auto Mode: "), f"Uses {min(cpuCnt // 2, 4)} threads (CPU cores: {cpuCnt})"]),
                    htm.Li([htm.B("Manual Mode: "), "Manually adjust thread count. More threads may be faster but consume more resources"]),
                    htm.Li([htm.B("Suggested: "), f"For {cpuCnt}-core CPU, recommend {min(cpuCnt // 2, 8)} threads"])
                ])
            ], className="irow"),
        ])
    ], className="mb-2")



@cbk(
    [
        out(k.id(k.gpuBatchSize), "disabled"),
    ],
    inp(k.id(k.gpuAutoMode), "value"),
    inp(k.id(k.gpuBatchSize), "value"),
    prevent_initial_call=True
)
def gpuSettings_OnUpd(autoMode, batchSize):
    db.dto.gpuAutoMode = autoMode
    db.dto.gpuBatchSize = batchSize

    lg.info(f"[gpuSets:OnUpd] AutoMode[{autoMode}] BatchSize[{batchSize}]")

    dis = autoMode
    return [dis]


@cbk(
    [
        out(k.id(k.cpuWorkers), "disabled"),
    ],
    inp(k.id(k.cpuAutoMode), "value"),
    inp(k.id(k.cpuWorkers), "value"),
    prevent_initial_call=True
)
def cpuSettings_OnUpd(autoMode, workers):
    db.dto.cpuAutoMode = autoMode
    db.dto.cpuWorkers = workers

    lg.info(f"[cpuSets:OnUpd] AutoMode[{autoMode}] Workers[{workers}]")

    dis = autoMode
    return [dis]


@cbk(
    out({"type": "mrg", "field": ALL}, "disabled"),
    inp({"type": "mrg", "field": ALL}, "value"),
    prevent_initial_call=True
)
def mrg_OnUpd(values):
    m = db.dto.mrg

    fields = []
    for item in ctx.inputs_list[0]:
        fld = item['id']['field']
        val = item['value']
        fields.append(fld)
        setattr(m, fld, val)

    lg.info(f"[mrg:OnUpd] {m}")
    return [False if f == 'on' else not m.on for f in fields]


def _chkPathIcon(localPth):
    import os
    if not localPth: return htm.I(className="bi bi-dash-circle text-muted")
    if os.path.exists(localPth): return htm.I(className="bi bi-check-circle-fill text-success")
    return htm.I(className="bi bi-x-circle-fill text-danger")

def _renderLibPathRows():
    import os
    libPaths = db.dto.pathLibs or {}
    if not libPaths: return htm.Div("No external libraries. Fetch assets to detect libraries.", className="text-muted txt-sm")

    rows = []
    for idx, (immichPth, localPth) in enumerate(libPaths.items()):
        rows.append(
            htm.Div([
                htm.Div([
                    htm.Small("Immich Path", className="text-muted"),
                    dbc.Input(value=immichPth, size="sm", className="txt-sm", disabled=True),
                ], className="col-5"),
                htm.Div([
                    htm.Small("Local Path", className="text-muted"),
                    dbc.InputGroup([
                        dbc.Input(
                            id=k.libPathId(idx),
                            value=localPth or "",
                            placeholder="Leave empty if same path",
                            size="sm",
                            className="txt-sm",
                            debounce=1000
                        ),
                        dbc.InputGroupText(
                            id=k.libPathChk(idx),
                            children=_chkPathIcon(localPth),
                            style={"padding": "0 8px"}
                        ),
                    ], size="sm"),
                ], className="col-7"),
            ], className="row mb-2 align-items-end", **{"data-immich-path": immichPth})
        )
    return htm.Div(rows)


def renderLibPaths():
    return dbc.Row([
        dbc.Col([
            #------------------------------------------------------------------------
            dbc.Card([
                dbc.CardHeader("Main Paths"),
                dbc.CardBody([
                    htm.Div([
                        htm.Small("Immich Path", className="text-muted"),
                        dbc.InputGroup([
                            dbc.Input(
                                id=k.id(k.immichPath),
                                value=db.dto.pathImmich or "",
                                placeholder="/path/to/immich",
                                size="sm",
                                className="txt-sm",
                                debounce=1000
                            ),
                            dbc.InputGroupText(
                                id=k.id(f"{k.immichPath}Chk"),
                                children=_chkPathIcon(db.dto.pathImmich),
                                style={"padding": "0 8px"}
                            ),
                        ], size="sm"),
                    ], className="mb-2"),
                    htm.Div([
                        htm.Small(["Thumbnail ", htm.Span("(optional)", className="text-muted")], className="text-muted"),
                        dbc.InputGroup([
                            dbc.Input(
                                id=k.id(k.immichThumb),
                                value=db.dto.pathThumb or "",
                                placeholder="/path/to/immichthumbs",
                                size="sm",
                                className="txt-sm",
                                debounce=1000
                            ),
                            dbc.InputGroupText(
                                id=k.id(f"{k.immichThumb}Chk"),
                                children=_chkPathIcon(db.dto.pathThumb),
                                style={"padding": "0 8px"}
                            ),
                        ], size="sm"),
                    ]),
                ])
            ], className="ifns mb-2"),
        ], width=4),
        dbc.Col([
            #------------------------------------------------------------------------
            dbc.Card([
                dbc.CardHeader([
                    "Library Mapping",
                    htm.Small("for external libraries", className="ms-2 text-muted")
                ]),
                dbc.CardBody([
                    htm.Div(id=k.id(k.libPathsContainer), children=_renderLibPathRows()),
                    htm.Ul([
                        htm.Li([htm.B("Immich Path: "), "Original path from Immich external library"]),
                        htm.Li([htm.B("Local Path: "), "Override path if Deduper can't access original"]),
                    ], className="mt-2 txt-sm text-muted")
                ])
            ], className="ifns mb-2"),
            #------------------------------------------------------------------------
            dcc.Store(id=k.id(k.libPathsData), data=json.dumps(db.dto.pathLibs or {})),

        ], width=8),
    ])



@cbk(
    [
        out(k.id(k.libPathsContainer), "children"),
        out(k.id(k.libPathsData), "data", allow_duplicate=True),
    ],
    inp(ks.sto.cnt, "data"),
    prevent_initial_call=True
)
def libPaths_OnCntUpd(_):
    db.dto.clearCache()
    libPaths = db.dto.pathLibs or {}
    return _renderLibPathRows(), json.dumps(libPaths)


@cbk(
    out(k.id(k.libPathsData), "data"),
    inp({"type": "libPath", "idx": ALL}, "value"),
    ste(k.id(k.libPathsData), "data"),
    prevent_initial_call=True
)
def libPaths_OnUpd(values, dataJson):
    libPaths = json.loads(dataJson) if dataJson else {}
    keys = list(libPaths.keys())

    for idx, val in enumerate(values):
        if idx < len(keys): libPaths[keys[idx]] = val or ""

    db.dto.pathLibs = libPaths
    lg.info(f"[libPaths:OnUpd] Updated {len(libPaths)} mappings")

    return json.dumps(libPaths)


@cbk(
    out({"type": "libPathChk", "idx": ALL}, "children"),
    inp({"type": "libPath", "idx": ALL}, "value"),
    ste(k.id(k.libPathsData), "data"),
    prevent_initial_call=True
)
def libPathChk_OnUpd(values, dataJson):
    icons = []
    for val in values: icons.append(_chkPathIcon(val))
    return icons


@cbk(
    out(k.id(f"{k.immichPath}Chk"), "children"),
    inp(k.id(k.immichPath), "value"),
    prevent_initial_call=True
)
def immichPath_OnUpd(val):
    db.dto.pathImmich = val or ""
    lg.info(f"[immichPath:OnUpd] Updated to: {val}")
    return _chkPathIcon(val)


@cbk(
    out(k.id(f"{k.immichThumb}Chk"), "children"),
    inp(k.id(k.immichThumb), "value"),
    prevent_initial_call=True
)
def immichThumb_OnUpd(val):
    db.dto.pathThumb = val or ""
    lg.info(f"[immichThumb:OnUpd] Updated to: {val}")
    return _chkPathIcon(val)


ccbk(
    cbkFn("ui", "toggleGridInfo"),
    out({"type": "dummy", "id": "grid-info"}, "children"),
    inp(k.id(k.showGridInfo), "value"),
    prevent_initial_call=False
)
