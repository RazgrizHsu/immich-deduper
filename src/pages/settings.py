from conf import ks, envs
from dsh import dash, htm, dbc, dcc
from util import log

import rtm
from ui import cardSets

lg = log.get(__name__)

dash.register_page(
    __name__,
    path=f'/',
    title=f"{ks.title}: " + 'System Settings',
)


#========================================================================
def layout():
    import ui

    return ui.renderBody([
        #====== top start =======================================================

        htm.Div([
            htm.H3(f"{ks.pg.setting.name}"),
            htm.Small(f"{ks.pg.setting.desc}", className="text-muted")
        ], className="body-header"),

        htm.Div([
            htm.Div([
                dbc.Card([
                    dbc.CardHeader([
                        "System Configuration"
                    ]),
                    dbc.CardBody([

                        htm.Div([
                            dbc.Row([
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("Deduper Data", className="text-muted ms-2"),
                                    htm.Div(envs.ddupData or "(Not configured)", className="fw-semibold text-break small")
                                ], className="p-2 rounded chk-data"), width=6),
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("Immich Logic", className="text-muted ms-2"),
                                    htm.Div("GitHub Repository", className="fw-semibold small")
                                ], className="p-2 rounded chk-logic"), width=6),
                            ], className="mb-2"),
                            dbc.Row([
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("Qdrant", className="text-muted ms-2"),
                                    htm.Div(envs.qdrantUrl or "(Not configured)", className="fw-semibold text-break small")
                                ], className="p-2 rounded chk-vec"), width=6),
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("PostgreSQL", className="text-muted ms-2"),
                                    htm.Div(f"{envs.psqlHost}:{envs.psqlPort}", className="fw-semibold small")
                                ], className="p-2 rounded chk-psql"), width=6),
                            ], className="mb-2"),
                            dbc.Row([
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("Immich Path", className="text-muted ms-2"),
                                    htm.Div(rtm.immichPath or "(Not configured)", className="fw-semibold text-break small")
                                ], className="p-2 rounded chk-path"), width=6),
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("ResNet152", className="text-muted ms-2"),
                                    htm.Div("Feature Extraction", className="fw-semibold small")
                                ], className="p-2 rounded chk-model"), width=6),
                            ], className="mb-2"),
                            dbc.Row([
                                dbc.Col(htm.Div([
                                    htm.I(), htm.Small("ExifTool", className="text-muted ms-2"),
                                    htm.Div("Metadata Editor", className="fw-semibold small")
                                ], className="p-2 rounded chk-exiftool"), width=6),
                            ], className="mb-2"),
                        ], className="card-system-cfgs")
                    ])
                ], className="border-0 shadow-sm")
            ], className="col-lg-10 mb-4"),


            htm.Div([

                cardSets.renderThreshold(),

                cardSets.renderCard(),


            ], className="border-0 shadow-sm")

        ], className="row"),
        #====== top end =========================================================
    ], [
        #====== bottom start=====================================================

        #====== bottom end ======================================================
    ])
