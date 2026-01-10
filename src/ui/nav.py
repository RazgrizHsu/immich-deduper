
from conf import ks
from dsh import htm, dbc, inp, out, cbk
from util import log
from mod import tsk, models
lg = log.get(__name__)

#========================================================================
class k:
    fth = 'nav-fetch'
    vec = 'nav-vector'
    sim = 'nav-similar'
    view = 'nav-view'


#========================================================================
def renderHeader():
    defs = [
        dbc.NavLink(htm.Span([f"⚙️ {ks.pg.setting.name}"]), href=f"/", active="exact", className="navLnk"),
        dbc.NavLink(htm.Span([f"⚡️ {ks.pg.fetch.name}"]), href=f"/{ks.pg.fetch}", active="exact", id=k.fth, className="navLnk", disabled=True),
        dbc.NavLink(htm.Span([f"🔄 {ks.pg.vector.name}"]), href=f"/{ks.pg.vector}", active="exact", id=k.vec, className="navLnk", disabled=True),
        dbc.NavLink(htm.Span([f"🔍 {ks.pg.similar.name}"]), href=f"/{ks.pg.similar}", active="exact", id=k.sim, className="navLnk", disabled=True),
        dbc.NavLink(htm.Span([f"🖼️ {ks.pg.view.name}"]), href=f"/{ks.pg.view}", active="exact", id=k.view, className="navLnk", disabled=True),
    ]

    return dbc.Navbar(
        dbc.Container([
            htm.A(
                dbc.Row([
                    dbc.Col(htm.Img(src="assets/logo.png", height="38px"), width="auto", className="px-1"),
                    dbc.Col(dbc.NavbarBrand(f"{ks.title}", className="ms-2")),
                ],
                    align="center", className="g-0",
                ),
                href="/", style={"textDecoration": "none"},
            ),

            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),

            dbc.Collapse(
                dbc.Nav([dbc.NavItem(lnk) for lnk in defs], className="ms-auto", navbar=True),
                id="navbar-collapse", navbar=True,
            ),
        ],
            fluid=True
        ),
        color="dark", dark=True, className="px-1 nav-glow"
    )


#========================================================================
def renderFooter():
    return htm.Div(
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    htm.Div([
                        f"{ks.title} © 2025 ",
                        htm.A(" GitHub ", href="https://github.com/RazgrizHsu/immich-deduper", target="_blank")
                    ], className="text-center text-sm"),
                    width=12
                ),
            ]),
        ], fluid=True
        ),
        className="footer bg-dark"
    )


#========================================================================
def renderBody(top, bottom):
    return htm.Div([

        htm.Div(
            [
                *top,
            ],
            className="main"
        ),

        tsk.render(),

        *bottom

    ], className="body")


#========================================================================
#------------------------------------------------------------------------
@cbk(
    out(k.fth, 'disabled'),
    out(k.vec, 'disabled'),
    out(k.sim, 'disabled'),
    out(k.view, 'disabled'),
    inp(ks.sto.cnt, 'data'),
    inp(ks.sto.sys, 'data')
)
def ui_updNav(dta_cnt, dta_sys):
    if not dta_cnt or not dta_sys: return True, True, True, True

    cnt = models.Cnt.fromDic(dta_cnt)
    sys = models.Sys.fromDic(dta_sys)

    if not sys.ok: return True, True, True, True

    disFth = not sys.ok
    disVec = disFth or cnt.ass <= 0
    disSim = disFth or cnt.vec <= 0
    disView = disVec
    lg.info(f'[nav] sys:{sys}, disables: fth:{disFth}, vec:{disVec}, sim:{disSim}, view:{disView} cnt:{cnt}')

    return disFth, disVec, disSim, disView

