from typing import List
from dsh import htm, dbc
from conf import co
from util import log
from mod import models
import db


lg = log.get(__name__)

from ui import gvExif


def mkGrid(assets: list[models.Asset], minW=230, maxW=300, onEmpty=None):
    if not assets or len(assets) == 0:
        if onEmpty:
            if isinstance(onEmpty, str):
                return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
            else:
                return onEmpty
        return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

    cntAss = len(assets)

    if cntAss <= 4:
        styGrid = {
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "1rem",
            "justifyContent": "center"
        }
        styItem = {"flex": f"1 1 {minW}px"}
    else:
        styGrid = {
            "display": "grid",
            "gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
            "gap": "1rem"
        }
        styItem = {}

    rows = []
    firstRels = False

    cntRelats = sum(1 for a in assets if a.vw.isRelats)

    for idx, a in enumerate(assets):
        card = mkCard(a)

        if a.vw.isRelats and not firstRels:
            firstRels = True
            rows.append(htm.Div( htm.Label(f"relates ({cntRelats}) :"), className="hr"))

        rows.append(htm.Div(card, style=styItem))

    lg.info(f"[sim:gv] assets[{len(assets)}] rows[{len(rows)}]")

    return htm.Div(rows, className="gv", style=styGrid)


def mkGroupGrid(assets: List[models.Asset], minW=250, maxW=300, onEmpty=None):
    if not assets or len(assets) == 0:
        if onEmpty:
            if isinstance(onEmpty, str):
                return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
            else:
                return onEmpty
        return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

    cntAss = len(assets)

    if cntAss <= 4:
        styGrid = {
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "1rem",
            "justifyContent": "center"
        }
        styItem = {"flex": f"1 1 {minW}px"}
    else:
        styGrid = {
            "display": "grid",
            "gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
            "gap": "1rem"
        }
        styItem = {}

    groups = {}
    for asset in assets:
        grpId = asset.vw.muodId or 0
        if grpId not in groups: groups[grpId] = []
        groups[grpId].append(asset)

    rows = []
    for grpId in sorted(groups.keys()):
        grpAssets = groups[grpId]
        grpCount = len(grpAssets)


        rows.append(htm.Div([
            htm.Label(f"Group {grpId} ( {grpCount} items )", className="me-3"),

            dbc.Button( [ htm.Span( className="fake-checkbox checked" ), "select this group all"], size="sm", color="secondary", id=f"cbx-sel-grp-all-{grpId}", className="txt-sm me-1" ),
            dbc.Button( [ htm.Span( className="fake-checkbox" ),"deselect this group All"], size="sm", color="secondary", id=f"cbx-sel-grp-non-{grpId}", className="txt-sm" ),

        ], className="hr"))

        for asset in grpAssets:
            card = mkCard(asset)
            rows.append(htm.Div(card, style=styItem))

    lg.info(f"[fsp:gv] assets[{len(assets)}] groups[{len(groups)}] rows[{len(rows)}]")

    return htm.Div(rows, className="gv fsp", style=styGrid)



def mkCard(ass: models.Asset):
    if not ass: return htm.Div("Photo not found")

    imgSrc = f"/api/img/{ass.autoId}" if ass.id else None

    checked = False
    cssIds = "checked" if checked else ""

    exi = ass.jsonExif
    ex = ass.ex

    imgW = exi.exifImageWidth
    imgH = exi.exifImageHeight

    isMain = ass.vw.isMain
    isRels = ass.vw.isRelats
    isLvPh = ass.vdoId

    css = f"h-100 sim {cssIds}"
    if isMain: css += " main"
    if isRels: css += " rels"

    return dbc.Card([
        dbc.CardHeader(
            htm.Div([
                dbc.Row([
                    dbc.Col(
                        dbc.Checkbox(label=f"#{ass.autoId}", value=False)
                    ),
                    dbc.Col(
                        [
                            htm.Span(f"Main", className="tag info lg ms-1")
                        ]
                        if isMain else
                        [
                            htm.Span("score:", className="tag sm info no-border"),
                            htm.Span(f"{ass.vw.score:.5f}", className="tag lg ms-1")
                        ]
                        if isRels else
                        [
                            htm.Span("score: ", className="tag sm second no-border"),
                            htm.Span(f"{ass.vw.score:.5f}", className="tag lg ms-1")
                        ]
                    )
                ])
            ], id={"type": "card-select", "id": ass.autoId}),
            className=f"p-2 curP"
        ),
        htm.Div([

            htm.Video(
                src=f"/api/livephoto/{ass.autoId}", loop=True, muted=True, autoPlay=True,
                id={"type": "img-pop-multi", "aid": ass.autoId}, n_clicks=0,
                className="livephoto-video",
            )
            if isLvPh else

            htm.Img(
                src=imgSrc,
                id={"type": "img-pop-multi", "aid": ass.autoId}, n_clicks=0,
                className=f"card-img"
            )

            if imgSrc else
            htm.Img(src="assets/noimg.png", className="card-img"),

            htm.Div([
                htm.Span(f"LivePhoto", className="tag blue") if isLvPh else None,
                htm.Span(f"SimOK!", className="tag blue") if ass.simOk else None,
                htm.Span([
                    htm.I(className='bi bi-images'),
                    f'{len(ex.albs)}'
                ], className='tag') if ex else None,

                htm.Span([
                    htm.I(className='bi bi-bookmark-check-fill'),
                    f'{len(ex.tags)}'
                ], className='tag') if ex else None,

                htm.Span([
                    htm.I(className='bi bi-person-bounding-box'),
                    f'{len(ex.tags)}'
                ], className='tag') if ex else None,
            ], className="RT"),

            htm.Div([
                htm.Span(f"#{ass.autoId}", className="tag"),
            ], className="LB"),
            htm.Div([

                htm.Span(f"{co.fmt.size(ass.jsonExif.fileSizeInByte)}", className="tag")
                if ass.jsonExif else None,
                htm.Span(f"{imgW} x {imgH}", className="tag lg"),
            ], className="RB")
        ], className="img"),
        dbc.CardBody([

            dbc.Row([
                htm.Span("id"), htm.Span(f"{ass.id}", className="tag"),
                htm.Span("device"), htm.Span(f"{ass.deviceId}", className="tag second txt-c"),
                htm.Span("FileName"), htm.Span(f"{ass.originalFileName}", className="tag second"),
                htm.Span("CreateAt"), htm.Span(f"{ass.fileCreatedAt}", className="tag second"),

                *([ htm.Span("livePhoto"), htm.Span(f"{ass.pathVdo}", className="tag blue"), ] if isLvPh else []),
                *([ htm.Span("live VdoId"), htm.Span(f"{ass.vdoId}", className="tag blue"), ] if isLvPh else []),

            ], class_name="grid"
            ) if db.dto.showGridInfo else None,
            htm.Div([

                # htm.Span("exif", className='tag info'),
                #
                # htm.Span([
                #     htm.I(className='bi bi-images'),
                #     f'{len(ex.albs)}'
                # ], className='tag') if ex else None,
                #
                # htm.Span([
                #     htm.I(className='bi bi-bookmark-check-fill'),
                #     f'{len(ex.tags)}'
                # ], className='tag') if ex else None,
                #
                # htm.Span([
                #     htm.I(className='bi bi-person-bounding-box'),
                #     f'{len(ex.tags)}'
                # ], className='tag') if ex else None,


                # htm.Span(f'', className=''),


            ], className=f'tagbox'),

            dbc.Row([
                htm.Table( htm.Tbody(gvExif.mkExifRows(ass)) , className="exif"),
            ]) if db.dto.showGridInfo else None,


        ], className="p-0"),
    ], className=css)



def mkPndGrid(assets: list[models.Asset], minW=230, maxW=300, onEmpty=None):
    if not assets or len(assets) == 0:
        if onEmpty:
            if isinstance(onEmpty, str):
                return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
            else:
                return onEmpty
        return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

    cntAss = len(assets)

    if cntAss <= 4:
        styGrid = {
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "1rem",
            "justifyContent": "start"
        }
        styItem = {"flex": f"1 1 {minW}px", "maxWidth": f"{maxW}px"}
    else:
        styGrid = {
            "display": "grid",
            "gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
            "gap": "1rem"
        }
        styItem = {}

    rows = [htm.Div(mkCardPnd(a), style=styItem) for a in assets]

    lg.info(f"[sim:gvPnd] assets[{len(assets)}] rows[{len(rows)}]")

    return htm.Div(rows, style=styGrid)


def mkCardPnd(ass: models.Asset, showRelated=True):

    imgSrc = f"/api/img/{ass.autoId}" if ass.autoId else "assets/noimg.png"

    if not ass.id: return htm.Div("-No ass.id-")

    assId = ass.id

    checked = False
    cssIds = "checked" if checked else ""

    exi = ass.jsonExif

    imgW = exi.exifImageWidth if exi else 0
    imgH = exi.exifImageHeight if exi else 0

    htmSimInfos = []

    htmRelated = None
    if ass.vw.cntRelats and showRelated:
        rids = []

        htmRelated = [
            htm.Hr(className="my-2"),
            htm.Div([
                htm.Span("Related groups: ", className="text-muted"),
                htm.Span(f"{ass.vw.cntRelats}", className="badge bg-warning")
            ]),
            htm.Div(rids)
        ]

    return dbc.Card([
        htm.Div([
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        "ViewGroup",
                        id={"type": "btn-view-group", "id": assId},
                        color="info",
                        size="sm",
                        className=""
                    )
                ),
                dbc.Col([
                    htm.Span("Matches: ", className="txt-sm"), htm.Span(f"{len(ass.simInfos) - 1}", className="tag lg ms-1 ps-2 pe-2")
                ], className="justify-content-end")
            ]
                , className="p-0")

        ], className="pt-2 ps-2 pb-3"),
        htm.Div([
            htm.Img(
                src=imgSrc,
                id={"type": "img-pop", "aid": ass.autoId}, n_clicks=0,
                className="card-img"
            ),
            htm.Div([
                htm.Span(f"#{ass.autoId}", className="tag sm second"),
            ], className="LB"),
            htm.Div([
                htm.Span(f"{imgW}", className="tag lg"),
                htm.Span("x"),
                htm.Span(f"{imgH}", className="tag lg"),
            ], className="RB")
        ], className="img"),
        dbc.CardBody([
            dbc.Row([
                htm.Span("id"), htm.Span(f"{ass.id}", className="badge bg-success text-truncate"),

            ], class_name="grid"),

            dbc.Row([
                htm.Span("fileName"), htm.Span(f"{ass.originalFileName}", className="text-truncate"),
                htm.Span("createAt"), htm.Span(f"{ass.fileCreatedAt}", className="text-truncate txt-sm"),

            ], class_name="grid2"),


            htm.Div(htmSimInfos),
            htm.Div(htmRelated),

        ], className="p-2")
    ], className=f"h-100 sim {cssIds}")

