window.dash_clientside = window.dash_clientside || {}

//============================================================================
// suppress page-specific callback errors for multi-page apply
// this is unfortunately a known limitation of the Dash multi-page framework
//
// if anyone have better solution, please tell me, thanks :)
//============================================================================
;(function(){
	const pageIds = ['sim-gvSim', 'sim-gvPnd', 'fetch-usr-select']
	const origErr = console.error
	console.error = function(...args){
		const msg = String(args[0]?.message || args[0] || '')
		if (msg.includes('nonexistent object')) {
			const matched = pageIds.find(id => msg.includes(id))
			if (matched) {
				console.debug(`[dash] skipped page-specific callback: ${matched}`)
				return
			}
		}
		if(msg.includes('Callback error updating')){
			console.debug(`[dash] hot reload...`)
			return
		}
		origErr.apply(console, args)
	}
})()

const R = {
	mk(t, props, ... children){return React.createElement(t, props, ... children)},
}

const fmtDate = (timestamp) =>{
	const dt = new Date(timestamp)
	const yr = dt.getFullYear()
	const mo = String(dt.getMonth() + 1).padStart(2, '0')
	const dy = String(dt.getDate()).padStart(2, '0')
	const hr = String(dt.getHours()).padStart(2, '0')
	const mn = String(dt.getMinutes()).padStart(2, '0')
	const sc = String(dt.getSeconds()).padStart(2, '0')
	return `${yr}${mo}${dy} ${hr}:${mn}:${sc}`
}



// ============================================================================
// getStore( key ) - Get store data by id
//   // string id
//   dsh.getStore( 'store-mdl' )
//   // -> { id: null, cmd: null, ok: false, args: {}, msg: null }
//
//   // pattern matching id (object)
//   dsh.getStore( { type: "pgr-vg-pager-main-store", idx: 0 } )
//   // -> { showInfo: true, avFirstLast: true, ... }
//
// syncStore( key, data ) - Update store data, triggers listening callbacks
//   key: string id of the store
//   data: new data object to set
//
//   // Update pager to page 3 (triggers pager UI update + content reload)
//   const pgr = dsh.getStore( 'vg-pager-main-store' )
//   dsh.syncStore( 'vg-pager-main-store', { ...pgr, idx: 3 } )
//
//   // Update modal store
//   dsh.syncStore( 'store-mdl', { id: 'test', cmd: 'xxx', ok: true } )
// ============================================================================
const dsh = {
	noUpd: window.dash_clientside.no_update,
	syncStore(key, data){

		if (!window.dash_clientside || !window.dash_clientside.set_props) {
			console.error(`[mdlImg] error not found dash client side...`)
			return
		}
		let typ = typeof data
		let str = `data(${typeof data})`

		if (typ == 'object') {
			const entries = Object.entries(data).map(([k, v]) => `${k}: (${typeof v})[${v}]`).join(', ')
			str += ` entries: {${entries}}`
		}
		else {
			str += data
		}
		console.info(`[dsh] sync store[ ${key} ] ${str}`)

		window.dash_clientside.set_props(key, {data: data}) //use dcc.Store need data property
	},

	getStore(key){
		const api = window.dash_component_api
		if (!api) return null
		const layout = api.getLayout(key)
		return layout && layout.props && layout.props.data
	},

	syncSte(cnt, selectedIds){
		if (!Array.isArray(selectedIds)) selectedIds = Array.from(selectedIds)
		this.syncStore('store-state', {cntTotal: cnt, selectedIds: selectedIds})
	}
}



function onFetchedChk(loading, data){
	console.info(`[load] check data: ${JSON.stringify(data)}`)

	let errK = false
	let verItem = null

	let sc = document.querySelector('.card-system-cfgs')
	if (sc) {
		for ( let item of data){
			if (item.key === 'ver') {verItem = item; continue}
			if (!item.ok && !errK) errK = item.key

			let div = sc.querySelector(`.chk-${item.key}`)
			if (!div) continue

			let i = div.querySelector(`i`)
			if (!i) continue

			if (!item.ok) {
				i.className = `bi bi-x-circle-fill text-white me-2`
				div.classList.add(`bg-danger`, `text-white`, `divtip`)
				let errorMsg = item.msg.join('\n')
				div.setAttribute('data-tooltip', errorMsg)
				div.style.cursor = 'help'
			}
			else {
				i.className = `bi bi-check-circle-fill text-success me-2`
				div.classList.remove(`divtip`)
				div.removeAttribute('data-tooltip')
				div.style.cursor = 'default'
			}
		}
	}

	TskWS.init(
		() =>{
			let sp = document.querySelector('#span-sys-chk')
			if (!sp) {Nfy.error(`[chk] span-sys-chk not exist?`); return}
			if (!errK) {
				sp.innerText = `ok`
				sp.classList.add('info')
			}
			else {
				sp.innerText = `Failed: ${errK}`
				sp.classList.add('red')
			}

			if (verItem && !verItem.ok) {
				let msg = verItem.msg.join('\n')
				let isNewVer = msg.includes('New version')

				if (isNewVer) {
					Nfy.warn(msg, 10000)
				} else {
					notify.load(msg, 'warn').run(30000)
				}

				sp.innerText = verItem.msg[0]
				sp.classList.remove('info',`second`)
				sp.classList.add('warn')
			} else if (verItem) sp.innerText = `ver:${verItem.msg[0]}`


			if (!errK) {
				loading.close()

				dsh.syncStore('store-sys', {ok: true})
				Nfy.info(`system check ok!`)
				return
			}

			loading.close()
			notify.erro(`system check failed`)
			Nfy.error(`[system] check ${errK} failed, please check your environment - ${fmtDate(Date.now())}`)

		},
		(msg) =>{
			let sp = document.querySelector('#span-sys-chk')
			if (!sp) {Nfy.error(`[chk] span-sys-chk not exist?`); return}
			sp.innerText = msg ? `Failed: ${msg}` : `Failed`
			sp.classList.add('red')
			loading.closeNo(`system check failed, ${msg}`)
		}
	)
}

document.addEventListener('DOMContentLoaded', function(){

	ui.mob.waitFor('#div-notify', cbx =>{

		let ld = notify.load('Please wait, system checking...').run()
		fetch('/api/chk').then(rep => rep.json())
			.then(data =>onFetchedChk(ld, data))
			.catch(error =>notify(`[wst] Failed to get System Check Status, ${error}`, 'warn'))
	})

})

