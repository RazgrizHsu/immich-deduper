from dsh import htm, dcc, dbc, inp, out, ste, cbk
from mod import models
from conf import ks, envs
import conf

class k:
    connInfo = 'div-conn-info'
    sideState = 'div-side-state'
    cardEnv = 'env-card-body'
    cardCnt = 'cache-card-body'

def getStatusIcon(ok: bool):
    if ok: return htm.I(className="bi bi-check-circle-fill text-success")
    return htm.I(className="bi bi-x-circle-fill text-danger")

def layout():
    return htm.Div([
        dbc.Card([
            dbc.CardHeader("env"),
            dbc.CardBody(id=k.cardEnv, children=[
                htm.Div( "connecting..." )
            ], className="igrid")
        ], className="mb-2"),

        dbc.Card([
            dbc.CardHeader("Cache Count"),
            dbc.CardBody(id=k.cardCnt, children=[
                htm.Div( "counting..." )
            ])
        ]),
    ],
        className="sidebar"
    )


@cbk(
    [
        out(k.cardEnv, "children"),
        out(k.cardCnt, "children"),
        out(ks.sto.nfy, "data", allow_duplicate=True),
    ],
    inp(ks.sto.init, "children"),
    inp(ks.sto.cnt, "data"),
    ste(ks.sto.nfy, "data"),

    prevent_initial_call="initial_duplicate",
)
def onUpdateSideBar(_trigger, dta_count, dta_nfy):
    cnt = models.Cnt.fromDic(dta_count)
    nfy = models.Nfy.fromDic(dta_nfy)

    dvcType = conf.device.type
    if dvcType == 'cuda':
        import torch
        try:
            gpuNam = torch.cuda.get_device_name(0)
            gpuMem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            dvcInfo = f"NVIDIA {gpuNam[:10]}... ({gpuMem:.1f}GB)"
            dvcStyle = "tag info"
        except:
            dvcInfo = "CUDA GPU"
            dvcStyle = "tag info"
    elif dvcType == 'mps':
        try:
            import platform
            processor = platform.processor() or "Apple Silicon"
            import psutil
            cMem = psutil.virtual_memory().total / (1024**3)
            dvcInfo = f"Apple {processor} ({cMem:.1f}GB)"
            dvcStyle = "tag info"
        except:
            dvcInfo = "Apple MPS"
            dvcStyle = "tag info"
    else:
        import multiprocessing
        cCpu = multiprocessing.cpu_count()
        dvcInfo = f"CPU ({cCpu} cores)"
        dvcStyle = "tag"

    envRows = [
        dbc.Row([
            dbc.Col(htm.Small("system"), width=3),
            dbc.Col(htm.Span( "loading..", id="span-sys-chk", className="tag second"))
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(htm.Small("device"), width=3),
            dbc.Col(htm.Span(dvcInfo, className=f"{dvcStyle} warp", title=f"Device: {conf.device}"))
        ], className="mb-2"),
    ]

    sizeL = 3

    cacheRows = [
        dbc.Row([
            dbc.Col(htm.Small("Assets", className="d-inline-block me-2"), width=sizeL),
            dbc.Col(htm.Span(f"{cnt.ass}", className="tag px-3 mb-2 txt-c")),
        ]),
        dbc.Row([
            dbc.Col(htm.Small("Vectors", className="d-inline-block me-2"), width=sizeL),
            dbc.Col(htm.Span(f"{cnt.vec}", className="tag px-3 mb-2 txt-c")),
        ], className="mb-1"),

        dbc.Row([
            dbc.Col(htm.Small("Resolve", className="d-inline-block me-2"), width=sizeL),
            dbc.Col(
                htm.Div([
                    htm.Span(f"{cnt.simOk}", className="tag info txt-c"), " / ",
                    htm.Span(f"{cnt.simNo}", className="tag second txt-c")
                ],
                    style={ "display":"grid", "gridTemplateColumns":"1fr auto 1fr" }
                )
            ) ,
        ]),
        dbc.Row([
            dbc.Col(htm.Small("Pending", className="d-inline-block me-2"), width=sizeL),
            dbc.Col(htm.Span(f"{cnt.simPnd}", className="tag blue px-3 mb-2 text-center")),
        ]),
    ]

    return envRows, cacheRows, nfy.toDict()
