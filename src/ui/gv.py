from typing import List
from dsh import htm, dbc
from conf import ks
from util import log
from mod import models


lg = log.get(__name__)

from ui import gvEx, cards


def mkGrd(assets: list[models.Asset], minW=230, onEmpty=None, maker=cards.mk):
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
        card = maker(a)


        if a.vw.isRelats and not firstRels:
            firstRels = True
            rows.append(htm.Div( htm.Label(f"relates ({cntRelats}) :"), className="hr"))

        rows.append(htm.Div(card, style=styItem))

    lg.info(f"[sim:gv] assets[{len(assets)}] rows[{len(rows)}]")

    return htm.Div(rows, className="gv", style=styGrid)


def mkGrdGrps(assets: List[models.Asset], minW=250, maxW=300, onEmpty=None):
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
            htm.Label(f"Group {grpId} ( {grpCount} items )"),

            dbc.Button( [ htm.Span( className="fake-checkbox checked" ), "select this group all"], size="sm", color="secondary", id=f"cbx-sel-grp-all-{grpId}", className="txt-sm me-1" ),
            dbc.Button( [ htm.Span( className="fake-checkbox" ),"deselect this group All"], size="sm", color="secondary", id=f"cbx-sel-grp-non-{grpId}", className="txt-sm" ),

        ], className="hr"))

        for asset in grpAssets:
            card = cards.mk(asset)
            rows.append(htm.Div(card, style=styItem))

    lg.info(f"[fsp:gv] assets[{len(assets)}] groups[{len(groups)}] rows[{len(rows)}]")

    return htm.Div(rows, className="gv fsp", style=styGrid)



def mkPndGrd(assets: list[models.Asset], minW=230, maxW=300, onEmpty=None):
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

    rows = [htm.Div(cards.mkCardPnd(a), style=styItem) for a in assets]

    lg.info(f"[sim:gvPnd] assets[{len(assets)}] rows[{len(rows)}]")

    return htm.Div(rows, style=styGrid)
