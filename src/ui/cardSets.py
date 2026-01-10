from dsh import htm, dcc, dbc, inp, out, ste, cbk, noUpd

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

    exclEnable = "exclEnable"
    exclFndLess = "exclFndLess"
    exclFilName = "exclFilName"

    muodEnable = "muodEnable"
    muodEqDate = "muodEqDate"
    muodEqWidth = "muodEqWidth"
    muodEqHeight = "muodEqHeight"
    muodEqSize = "muodEqSize"
    muodMaxGroups = "muodMaxGroups"

    muodAuSel = "muodAuSel"

    auSelEnable = "autoSelEnable"
    auSelSkipLowSim = "autoSelSkipLowSim"
    auSelAllLivePhoto = "auSelAllLivePhoto"

    auSelEarlier = "autoSelEarlier"
    auSelLater = "autoSelLater"
    auSelExifRicher = "autoSelExifRicher"
    auSelExifPoorer = "autoSelExifPoorer"
    auSelBiggerSize = "autoSelBiggerSize"
    auSelSmallerSize = "autoSelSmallerSize"
    auSelBiggerDimensions = "autoSelBiggerDimensions"
    auSelSmallerDimensions = "autoSelSmallerDimensions"
    auSelNameLonger = "autoSelNameLonger"
    auSelNameShorter = "autoSelNameShorter"
    auSelTypeJpg = "autoSelTypeJpg"
    auSelTypePng = "autoSelTypePng"
    auSelTypeHeic = "autoSelTypeHeic"
    auSelFav = "autoSelFav"
    auSelInAlb = "autoSelInAlb"

    gpuAutoMode = "gpuAutoMode"
    gpuBatchSize = "gpuBatchSize"

    cpuAutoMode = "cpuAutoMode"
    cpuWorkers = "cpuWorkers"


    @staticmethod
    def id(name): return {"type": "sets", "id": f"{name}"}


optThresholdMin = 0.5
optThresholdMarks = { "0.5":0.5, "0.6":0.6, "0.7": 0.7, "0.8": 0.8, "0.9": 0.9, "1": 1 }

optMaxDepths = []
for i in range(6): optMaxDepths.append({"label": f"{i}", "value": i})

optMaxItems = []
for i in [10, 50, 100, 200, 300, 500, 1000]: optMaxItems.append({"label": f"{i}", "value": i})

optMaxGroups = []
for i in [2, 5, 10, 20, 25, 50, 100]: optMaxGroups.append({"label": f"{i}", "value": i})

optWeights = []
for i in range(5): optWeights.append({"label": f"{i}", "value": i})

optExclLess = [
    {"label": "--", "value": 0},
]
for i in range(1,6): optExclLess.append({"label": f" < {i}", "value": i})

optGpuBatch = {}
for i in [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]: optGpuBatch[str(i)] = i

optCpuWorkers = {}
import multiprocessing
cpuCnt = multiprocessing.cpu_count()
if cpuCnt is None: cpuCnt = multiprocessing.cpu_count()
for i in range(1, min(cpuCnt + 1, 17)): optCpuWorkers[str(i)] = i

def renderThreshold():
    return dbc.Card([
        dbc.CardHeader("Threshold Min"),
        dbc.CardBody([
            htm.Div([
                htm.Div([
                    dcc.Slider(
                        id=k.id(k.threshold), min=optThresholdMin, max=1, step=0.01, marks=optThresholdMarks, #type: ignore
                        value=db.dto.thMin, included=False,
                        tooltip={
                            "placement": "top", "always_visible": True,
                            "style": {"padding": "0 1px 0 1px", "fontSize": "11px"},
                        },
                    ),
                ], className=""),
                htm.Ul([
                    htm.Li("Threshold sets minimum similarity for image matching")
                ])
            ], className="irow mb-2"),
        ])
    ], className="mb-2")

def renderAutoSelect():
    return dbc.Card([
        dbc.CardHeader("Auto Selection"),
        dbc.CardBody([
            htm.Div([
                # Main enable switch
                dbc.Checkbox(id=k.id(k.auSelEnable), label="Enable", value=db.dto.ausl), htm.Br(),

                dbc.Checkbox(id=k.id(k.auSelSkipLowSim), label="Skip has sim(<0.96) group", value=db.dto.ausl_SkipLow, disabled=not db.dto.ausl),

                dbc.Checkbox(id=k.id(k.auSelAllLivePhoto), label="All LivePhotos (ignore criteria)", value=db.dto.ausl_AllLive, disabled=not db.dto.ausl), htm.Br(),

                htm.Hr(),

                htm.Div([
                    htm.Span( htm.Span("DateTime", className="tag txt-smx me-1")),
                    htm.Label("Earlier", className="me-2"),
                    dbc.Select(id=k.id(k.auSelEarlier), options=optWeights, value=db.dto.ausl_Earlier, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Later", className="me-2"),
                    dbc.Select(id=k.id(k.auSelLater), options=optWeights, value=db.dto.ausl_Later, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Exif", className="tag txt-smx me-1")),
                    htm.Label("Richer", className="me-2"),
                    dbc.Select(id=k.id(k.auSelExifRicher), options=optWeights, value=db.dto.ausl_ExRich, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Poorer", className="me-2"),
                    dbc.Select(id=k.id(k.auSelExifPoorer), options=optWeights, value=db.dto.ausl_ExPoor, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Name Length", className="tag txt-smx me-1")),
                    htm.Label("Longer", className="me-2"),
                    dbc.Select(id=k.id(k.auSelNameLonger), options=optWeights, value=db.dto.ausl_NamLon, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Shorter", className="me-2"),
                    dbc.Select(id=k.id(k.auSelNameShorter), options=optWeights, value=db.dto.ausl_NamSht, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("FileSize", className="tag txt-smx me-1")),
                    htm.Label("Bigger", className="me-2"),
                    dbc.Select(id=k.id(k.auSelBiggerSize), options=optWeights, value=db.dto.ausl_OfsBig, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Smaller", className="me-2"),
                    dbc.Select(id=k.id(k.auSelSmallerSize), options=optWeights, value=db.dto.ausl_OfsSml, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("Dimensions", className="tag txt-smx me-1")),
                    htm.Label("Bigger", className="me-2"),
                    dbc.Select(id=k.id(k.auSelBiggerDimensions), options=optWeights, value=db.dto.ausl_DimBig, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Smaller", className="me-2"),
                    dbc.Select(id=k.id(k.auSelSmallerDimensions), options=optWeights, value=db.dto.ausl_DimSml, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Div([
                    htm.Span(htm.Span("File Type", className="tag txt-smx me-1")),
                    htm.Label("Jpg", className="me-2"),
                    dbc.Select(id=k.id(k.auSelTypeJpg), options=optWeights, value=db.dto.ausl_TypJpg, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Png", className="me-2"),
                    dbc.Select(id=k.id(k.auSelTypePng), options=optWeights, value=db.dto.ausl_TypPng, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("Heic", className="me-2"),
                    dbc.Select(id=k.id(k.auSelTypeHeic), options=optWeights, value=db.dto.ausl_TypHeic, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria icriteria-wrap"),

                htm.Div([
                    htm.Span(htm.Span("Immich", className="tag txt-smx me-1")),
                    htm.Label("Favorited", className="me-2"),
                    dbc.Select(id=k.id(k.auSelFav), options=optWeights, value=db.dto.ausl_Fav, disabled=not db.dto.ausl, size="sm", className="me-1"), #type:ignore
                    htm.Label("In Album", className="me-2"),
                    dbc.Select(id=k.id(k.auSelInAlb), options=optWeights, value=db.dto.ausl_InAlb, disabled=not db.dto.ausl, size="sm"), #type:ignore
                ], className="icriteria"),

                htm.Hr(),
                htm.Ul([
                    htm.Li("Automatically selects top assets in group"),
                    htm.Li([htm.B("Points: "),"0=Ignore, 1=Low, 2=High priority"])
                ], className="text-muted small")
            ], className="mb-2 igrid txt-sm"),
        ])
    ], className="mb-0")


def renderCard():
    return dbc.Card([
        dbc.CardHeader("Search Settings"),
        dbc.CardBody([
            htm.Div([
                htm.Label("Find Settings", className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.autoNext), label="Auto Find Next", value=db.dto.autoNext),
                    dbc.Checkbox(id=k.id(k.showGridInfo), label="Show Grid Info", value=db.dto.showGridInfo),

                    htm.Div([
                        htm.Label("Max Items: "),
                        dbc.Select(id=k.id(k.simMaxItems), options=optMaxItems, value=db.dto.rtreeMax, className="") #type:ignore
                    ]),
                ], className="icbxs"),
                htm.Ul([
                    htm.Li([htm.B("Max Items: "), "Max images to process in similarity search to prevent UI slowdown"])
                ])
            ], className="irow"),

            htm.Div([
                htm.Label("Related Tree", className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.simRtree), label="Related Tree", value=db.dto.rtree),

                ], className="icbxs"),
                htm.Ul([
                    htm.Li([htm.B("Related Tree: "), "Expand similar-tree to include relateds. Keep/Delete affects all displayed images"]),
                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Multi Mode",
                    htm.Span("Find multiple groups of similar photos (mutually exclusive with Related Tree)", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.muodEnable), label="Enable", value=db.dto.muod),

                    htm.Div([
                        htm.Label("Max Groups: "),
                        dbc.Select(id=k.id(k.muodMaxGroups), options=optMaxGroups, value=db.dto.muod_Size, className="", disabled=True) #type:ignore
                    ]),

                    htm.Br(),

                    dbc.Checkbox(id=k.id(k.muodEqDate), label="Same Date", value=db.dto.muod_EqDt, disabled=db.dto.muod),
                    dbc.Checkbox(id=k.id(k.muodEqWidth), label="Same Width", value=db.dto.muod_EqW, disabled=db.dto.muod),
                    dbc.Checkbox(id=k.id(k.muodEqHeight), label="Same Height", value=db.dto.muod_EqH, disabled=db.dto.muod),
                    dbc.Checkbox(id=k.id(k.muodEqSize), label="Same File Size", value=db.dto.muod_EqFs, disabled=db.dto.muod),


                ], className="icbxs"),
                htm.Ul([
                    htm.Li([htm.B("Max Groups: "), "Maximum number of groups to return when grouping is enabled"]),
                    htm.Li([
                        htm.Span("⚠️ ", style={"color": "orange"}),
                        "Auto-Resolve unmatched photos as resolved to prevent re-searching. Use Reset records to reset."
                    ])
                ])
            ], className="irow"),

            htm.Div([
                htm.Label([
                    "Exclude Settings",
                    htm.Span("", className="txt-smx text-muted ms-3")
                ], className="txt-sm"),
                htm.Div([
                    dbc.Checkbox(id=k.id(k.exclEnable), label="Enable", value=db.dto.excl),

                    htm.Div([
                        htm.Label("Similar Less: "),
                        dbc.Select(id=k.id(k.exclFndLess), options=optExclLess, value=db.dto.excl_FndLes, className="", disabled=not db.dto.excl) #type:ignore
                    ]),

                    htm.Div([
                        htm.Label("NameFilter"),
                        dbc.Input( id=k.id(k.exclFilName), maxlength=100, placeholder='separate by ","', value=db.dto.excl_FilNam, disabled=not db.dto.excl )
                        # dbc.Select(id=k.id(k.exclFndLess), options=optExclLess, value=db.dto.excl_FndLes, className="", disabled=not db.dto.excl) #type:ignore
                    ]),

                    # htm.Br(),
                    # dbc.Checkbox(id=k.id(k.cndGrpSameDate), label="Same Date", value=db.dto.simCondSameDate, disabled=db.dto.simCondGrpMode),

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
    ], className="mb-0")


@cbk(
    [
        out(ks.sto.now, "data", allow_duplicate=True),
        out(k.id(k.muodEqDate), "disabled"),
        out(k.id(k.muodEqWidth), "disabled"),
        out(k.id(k.muodEqHeight), "disabled"),
        out(k.id(k.muodEqSize), "disabled"),
        out(k.id(k.muodMaxGroups), "disabled"),
    ],
    inp(k.id(k.threshold), "value"),
    inp(k.id(k.autoNext), "value"),
    inp(k.id(k.showGridInfo), "value"),
    inp(k.id(k.simRtree), "value"),
    inp(k.id(k.simMaxItems), "value"),
    inp(k.id(k.muodEnable), "value"),
    inp(k.id(k.muodEqDate), "value"),
    inp(k.id(k.muodEqWidth), "value"),
    inp(k.id(k.muodEqHeight), "value"),
    inp(k.id(k.muodEqSize), "value"),
    inp(k.id(k.muodMaxGroups), "value"),
    ste(ks.sto.now, "data"),
    prevent_initial_call=True
)
def settings_OnUpd(th, auNxt, shGdInfo, rtree,  maxItems, muodEnable, muodDate, muodWidth, muodHeight, muodSize, maxGroups, dta_now):
    retNow = noUpd

    now = models.Now.fromDic(dta_now)

    db.dto.thMin = co.vad.float(th, 0.93, 0.50, 0.99)

    db.dto.autoNext = auNxt
    db.dto.rtreeMax = maxItems

    db.dto.muod = muodEnable
    db.dto.muod_EqDt = muodDate
    db.dto.muod_EqW = muodWidth
    db.dto.muod_EqH = muodHeight
    db.dto.muod_EqFs = muodSize
    db.dto.muod_Size = maxGroups

    # Control muod enable/disable states
    muodDisabled = not muodEnable
    maxGroupsDisabled = not muodEnable

    def reloadAssets():
        nonlocal retNow, now
        lg.info(f"[sets:OnUpd] reload, rtree[{db.dto.rtree}] muodMode[{db.dto.muod}]")
        now.sim.assCur = db.pics.getSimAssets(now.sim.assAid, db.dto.rtree if not db.dto.muod else False )
        retNow = now

    #now.sim.assCur = db.pics.getSimAssets(assId, db.dto.simRtree)

    if db.dto.showGridInfo != shGdInfo:
        db.dto.showGridInfo = shGdInfo
        if retNow == noUpd: reloadAssets()

    if db.dto.rtree != rtree:
        db.dto.rtree = rtree
        if retNow == noUpd: reloadAssets()

    # lg.info(f"[settings] changed: {ths}, {auNxt}, {shGdInfo}")

    return [retNow, muodDisabled, muodDisabled, muodDisabled, muodDisabled, maxGroupsDisabled]


@cbk(
    [
        out(k.id(k.auSelSkipLowSim), "disabled"),
        out(k.id(k.auSelAllLivePhoto), "disabled"),
        out(k.id(k.auSelEarlier), "disabled"),
        out(k.id(k.auSelLater), "disabled"),
        out(k.id(k.auSelExifRicher), "disabled"),
        out(k.id(k.auSelExifPoorer), "disabled"),
        out(k.id(k.auSelBiggerSize), "disabled"),
        out(k.id(k.auSelSmallerSize), "disabled"),
        out(k.id(k.auSelBiggerDimensions), "disabled"),
        out(k.id(k.auSelSmallerDimensions), "disabled"),
        out(k.id(k.auSelNameLonger), "disabled"),
        out(k.id(k.auSelNameShorter), "disabled"),
        out(k.id(k.auSelTypeJpg), "disabled"),
        out(k.id(k.auSelTypePng), "disabled"),
        out(k.id(k.auSelTypeHeic), "disabled"),
        out(k.id(k.auSelFav), "disabled"),
        out(k.id(k.auSelInAlb), "disabled"),
    ],
    inp(k.id(k.auSelEnable), "value"),
    inp(k.id(k.auSelSkipLowSim), "value"),
    inp(k.id(k.auSelAllLivePhoto), "value"),
    inp(k.id(k.auSelEarlier), "value"),
    inp(k.id(k.auSelLater), "value"),
    inp(k.id(k.auSelExifRicher), "value"),
    inp(k.id(k.auSelExifPoorer), "value"),
    inp(k.id(k.auSelBiggerSize), "value"),
    inp(k.id(k.auSelSmallerSize), "value"),
    inp(k.id(k.auSelBiggerDimensions), "value"),
    inp(k.id(k.auSelSmallerDimensions), "value"),
    inp(k.id(k.auSelNameLonger), "value"),
    inp(k.id(k.auSelNameShorter), "value"),
    inp(k.id(k.auSelTypeJpg), "value"),
    inp(k.id(k.auSelTypePng), "value"),
    inp(k.id(k.auSelTypeHeic), "value"),
    inp(k.id(k.auSelFav), "value"),
    inp(k.id(k.auSelInAlb), "value"),
    prevent_initial_call=True
)
def autoSelect_OnUpd(enable, skipLo, onlyLive, earl, late, exRich, exPoor, szBig, szSml, dimBig, dimSml, namLn, namSt, tJpg, tPng, tHeic, fav, inAlb):
    db.dto.ausl = enable
    db.dto.ausl_SkipLow = skipLo
    db.dto.ausl_AllLive = onlyLive
    db.dto.ausl_Earlier = earl
    db.dto.ausl_Later = late
    db.dto.ausl_ExRich = exRich
    db.dto.ausl_ExPoor = exPoor
    db.dto.ausl_OfsBig = szBig
    db.dto.ausl_OfsSml = szSml
    db.dto.ausl_DimBig = dimBig
    db.dto.ausl_DimSml = dimSml
    db.dto.ausl_NamLon = namLn
    db.dto.ausl_NamSht = namSt
    db.dto.ausl_TypJpg = tJpg
    db.dto.ausl_TypPng = tPng
    db.dto.ausl_TypHeic = tHeic
    db.dto.ausl_Fav = fav
    db.dto.ausl_InAlb = inAlb

    lg.info(f"[autoSel:OnUpd] Enable[{enable}] HighSim[{skipLo}] AlwaysPickLivePhoto[{onlyLive}] Earlier[{earl}] Later[{late}] ExifRich[{exRich}] ExifPoor[{exPoor}] BigSize[{szBig}] SmallSize[{szSml}] BigDim[{dimBig}] SmallDim[{dimSml}] namLn[{namLn}] namSt[{namSt}] jpg[{tJpg}] png[{tPng}] heic[{tHeic}] fav[{fav}] inAlb[{inAlb}]")

    # Control enable/disable states
    dis = not enable

    return [dis] * 17


@cbk(
    [
        out(k.id(k.exclFndLess), "disabled"),
        out(k.id(k.exclFilName), "disabled"),
    ],
    inp(k.id(k.exclEnable), "value"),
    inp(k.id(k.exclFndLess), "value"),
    inp(k.id(k.exclFilName), "value"),
    prevent_initial_call=True
)
def excludeSettings_OnUpd(enable, fndLess, filName):
    db.dto.excl = enable
    db.dto.excl_FndLes = fndLess
    db.dto.excl_FilNam = filName

    lg.info(f"[exclSets:OnUpd] Enable[{enable}] FndLess[{fndLess}] FilName[{filName}]")

    dis = not enable
    return [dis]


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
