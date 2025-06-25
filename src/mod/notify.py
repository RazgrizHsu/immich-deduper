from dsh import dash, htm, dbc, dcc, out, inp, ste, cbk, ccbk, cbkFn, ALL
from util import log
from mod import models
from conf import ks
import json

lg = log.get(__name__)

class k:
    succ = 'success'
    erro = 'error'
    warn = 'warning'
    info = 'info'

    divId = 'div-notify'
    addTrigger = 'hidden-add-trigger'
    autoRemoveTrigger = 'hidden-auto-remove-trigger'


def render():
    return htm.Div([
        htm.Div( id=k.divId, className="notify"),
        dcc.Store(id=k.addTrigger, storage_type='memory'),
        dcc.Store(id=k.autoRemoveTrigger, storage_type='memory'),
        htm.Div(id='dummy-output', style={'display': 'none'})
    ])


@cbk(
    out(k.divId, 'children'),
    inp(ks.sto.nfy, 'data')
)
def nfy_onRender(nfyData):
    if not nfyData or not nfyData.get('msgs') or not isinstance(nfyData['msgs'], list):
        return []

    elements = []
    msgs = nfyData['msgs']

    for idx, msgData in enumerate(msgs):
        msgId = msgData.get('id', idx)
        msgType = msgData.get('type', 'info')
        msgText = msgData.get('message', '')
        msgTimeout = msgData.get('timeout', 0)

        # 類型對應
        typeClass = msgType
        if typeClass == 'danger': typeClass = 'error'
        if typeClass == 'warning': typeClass = 'warn'

        # 處理換行符號
        textParts = []
        for part in str(msgText).split('\n'):
            if textParts: textParts.append(htm.Br())
            textParts.append(part)

        # 建立通知元件
        notifyEl = htm.Div([
            htm.Span(textParts),
            htm.Button('×',
                id={'type': 'nfy-rm', 'index': msgId},
                className='nfy-close'
            )
        ],
        className=f'box {typeClass}',
        style={'animationDelay': f'{idx * 100}ms'},
        key=f'nfy-{msgId}',
        **{'data-msg-id': msgId, 'data-msg-type': msgType, 'data-msg-timeout': msgTimeout}
        )

        elements.append(notifyEl)

    return elements

ccbk(
    "window.dash_clientside.notify.add",
    out(ks.sto.nfy, 'data', allow_duplicate=True),
    inp(k.addTrigger, 'data'),
    ste(ks.sto.nfy, 'data'),
    prevent_initial_call=True
)

@cbk(
    out(ks.sto.nfy, 'data', allow_duplicate=True),
    inp({'type': 'nfy-rm', 'index': ALL}, 'n_clicks'),
    ste(ks.sto.nfy, 'data'),
    prevent_initial_call=True
)
def nfy_onRemove(clks, nfyData):
    if not nfyData or not nfyData.get('msgs'): return dash.no_update
    
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update
    
    triggered = ctx.triggered[0]
    if not triggered['value']: return dash.no_update
    
    try:
        triggeredId = json.loads(triggered['prop_id'].split('.')[0])
        msgId = triggeredId['index']
        
        newMsgs = [msg for msg in nfyData['msgs'] if msg.get('id') != msgId]
        return {'msgs': newMsgs}
    except:
        return dash.no_update

ccbk(
    "window.dash_clientside.notify.autoRemove",
    out(ks.sto.nfy, 'data', allow_duplicate=True),
    inp(k.autoRemoveTrigger, 'data'),
    ste(ks.sto.nfy, 'data'),
    prevent_initial_call=True
)

