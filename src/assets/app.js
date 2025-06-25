window.dash_clientside = window.dash_clientside || {}

const R = {
	mk( t, props, ... children )
	{
		return React.createElement( t, props, ... children )
	},
}




const dsh = {
	noUpd: window.dash_clientside.no_update,
	syncStore( key, data )
	{

		if ( !window.dash_clientside || !window.dash_clientside.set_props )
		{
			console.error( `[mdlImg] error not found dash client side...` )
			return
		}
		let typ = typeof data
		let str = `data(${ typeof data })`

		if ( typ == 'object' )
		{
			const entries = Object.entries( data ).map( ( [ k, v ] ) => `${ k }: (${ typeof v })[${ v }]` ).join( ', ' )
			str += ` entries: {${ entries }}`
		}
		else
		{
			str += data
		}
		console.info( `[dsh] sync store[ ${ key } ] ${ str }` )

		window.dash_clientside.set_props( key, { data: data } ) //use dcc.Store need data property
	},

	// No get_props func
	// getStore( key )
	// {
	// 		return window.dash_clientside.get_props( key, 'data' )
	// },

	syncSte( cnt, selectedIds )
	{

		if ( !Array.isArray( selectedIds ) ) selectedIds = Array.from( selectedIds )

		this.syncStore( 'store-state', { cntTotal: cnt, selectedIds: selectedIds } )
	}
}



function onFetchedChk( loading, data ){
	console.info( `[load] check data: ${ JSON.stringify(data) }` )

	let errK = false

	let sc = document.querySelector('.card-system-cfgs')
	if( sc ) {

		let keys = ['logic', 'path', 'data', 'psql', 'vec']

		for( let idx in keys ) {
			let k = keys[idx]

			let ste = data[k]
			if( !ste.ok ) errK = k


			let div = sc.querySelector(`.chk-${k}`)
			if( !div ) continue

			let i = div.querySelector(`i`)
			let s = div.querySelector(`small`)
			if( !i || !s ) continue

			if( !ste.ok ) {
				i.className = `bi bi-x-circle-fill text-white me-2`
				div.classList.add(`bg-danger`, `text-white`, `divtip`)

				// tooltip
				let errorMsg = Array.isArray(ste.msg) ? ste.msg.join('\n') : ste.msg
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

	// update env card
	let sp = document.querySelector( "#span-sys-chk" )
	if( !sp ) {

		Nfy.error(`[chk] span-sys-chk not exist?`)
		return
	}

	TskWS.init(
		()=>{
			if( !errK ) {
				sp.innerText = `ok`
				sp.classList.add('info')
			}
			else {
				sp.innerText = `Failed: ${errK}`
				sp.classList.add('red')
			}

			if( !data.ver.ok ) {

				let msg = data.ver.msg.join( '\n' )
				notify.load( msg, 'warn' ).run( 30000 )

				sp.innerText = `please update`
				sp.classList.remove('info',`second`)
				sp.classList.add('warn')
			} else {
				sp.innerText =`ver:${data.ver.msg[0]}`
			}


			if ( !errK ){
				loading.close()

				dsh.syncStore('store-sys', { ok: true })
				Nfy.info( `system check ok!` )
				return
			}

			loading.close()
			notify.erro(`system check failed`)
			Nfy.error( `[system] check ${errK} failed, please check your environment - ${Date.now()}` )

		},
		( msg )=>{
			sp.innerText = `Failed`
			sp.classList.add('red')
			loading.closeNo( `system check failed, ${msg}` )
		}
	)
}

document.addEventListener( 'DOMContentLoaded', function(){

	let ld = notify.load( 'Please wait, system checking...' ).run()
	fetch( '/api/chk' ).then( rep => rep.json() )
	.then( data => {
		onFetchedChk(ld, data)
	} )
	.catch( error => {
		notify( `[wst] Failed to get System Check Status, ${error}`, 'warn')
	} )

} )

