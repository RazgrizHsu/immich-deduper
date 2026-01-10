from conf import ks, envs
from dsh import dash, htm, dbc, dcc
from util import log

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

                            htm.Div([
                                htm.Div([
                                    htm.I(),
                                    htm.Small("Deduper Data Path", className="text-muted")
                                ], className="d-flex align-items-center"),
                                htm.Div([
                                    htm.Span(envs.mkitData or "(Not configured)", className="fw-semibold text-break me-2"),
                                    htm.Span(className="small")
                                ], className="fw-semibold")
                            ], className=f"row mb-3 p-2 rounded chk-data"),


                            htm.Div([
                                htm.Div([
                                    htm.I(),
                                    htm.Small("Immich Logic Check", className="text-muted")
                                ], className="d-flex align-items-center"),
                                htm.Div([
                                    htm.Span("Immich GitHub Repository", className="fw-semibold me-2"),
                                    htm.Span(className="small")
                                ], className="fw-semibold")
                            ], className=f"row mb-3 p-2 rounded chk-logic"),

                            htm.Div([
                                htm.Div([
                                    htm.I(),
                                    htm.Small("Qdrant URL", className="text-muted")
                                ], className="d-flex align-items-center"),
                                htm.Div([
                                    htm.Span(envs.qdrantUrl or "(Not configured)", className="fw-semibold text-break me-2"),
                                    htm.Span(className="small")
                                ], className="fw-semibold")
                            ], className=f"row mb-3 p-2 rounded chk-vec"),

                            htm.Div([
                                htm.Div([
                                    htm.I(),
                                    htm.Small("PostgreSQL Connection", className="text-muted")
                                ], className="d-flex align-items-center"),
                                htm.Div([
                                    htm.Span(f"{envs.psqlHost}:{envs.psqlPort}", className="fw-semibold me-2"),
                                    htm.Span(className="small")
                                ], className="fw-semibold")
                            ], className=f"row mb-3 p-2 rounded chk-psql"),

                            htm.Div([
                                htm.Div([
                                    htm.I(),
                                    htm.Small("Immich Root Path", className="text-muted")
                                ], className="d-flex align-items-center"),
                                htm.Div([
                                    htm.Span(envs.immichPath or "(Not configured)", className="fw-semibold text-break me-2"),
                                    htm.Span(className="small")
                                ], className="fw-semibold")
                            ], className=f"row mb-3 p-2 rounded chk-path"),

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
