class Notice
{
	constructor( msg, type, iconClass )
	{
		this.msg = msg
		this.typ = type
		this.cssIco = iconClass
		this.el = null
	}

	run( timeout, rotating = true )
	{
		if ( timeout == true ) rotating = true

		let ncr = document.querySelector( '.js-notify' )
		if ( !ncr )
		{
			ncr = document.createElement( 'div' )
			ncr.classList.add( 'js-notify' )
			document.body.appendChild( ncr )
		}

		this.el = document.createElement( 'div' )
		this.el.classList.add( 'jsnfy' )
		if ( this.typ ) this.el.classList.add( this.typ )

		const box = document.createElement( 'div' )
		box.classList.add( 'box' )

		if ( this.cssIco )
		{
			const ico = document.createElement( 'i' )
			ico.className = `bi ${ this.cssIco }`
			if ( rotating ) ico.classList.add( 'rotating' )
			box.appendChild( ico )
		}

		const txt = document.createElement( 'span' )
		txt.innerHTML = this.msg.replace(/\n/g, '<br/>')
		box.appendChild( txt )

		this.el.appendChild( box )
		ncr.prepend( this.el )

		setTimeout( () => {
			this.el.style.opacity = 1
			this.el.style.transform = 'translateY(0)'
		}, 10 )

		if ( timeout )
		{
			let nfy = this
			setTimeout( () => { nfy.close() }, timeout )
		}
		return this
	}

	close(timeout)
	{
		let el = this.el
		let cls = () =>{

			if ( !el ) return
			el.style.opacity = 0
			el.style.transform = 'translateY(20px)'
			el.addEventListener( 'transitionend', function handler(){
				this.remove()
				this.removeEventListener( 'transitionend', handler )
			}, { once: true } )
		}
		( !timeout ) ? cls() : setTimeout(cls,timeout)

	}

	closeOk( txt, timeout = 3000, icon = 'bi-check-circle-fill' ) {
		const ico = this.el.querySelector('i')

		if ( ico ) {
			ico.className = ico.className.split(' ').filter(cls => !cls.startsWith('bi-') && cls != 'rotating').join(' ')
			ico.classList.add( icon )
			ico.classList.remove( 'rotating' )
		}
		let sp = this.el.querySelector('span')
		sp.textContent = `${txt}`

		this.close( timeout )
	}

	closeNo( txt, timeout = 3000, icon = 'bi-x-circle-fill' ) {
		const ico = this.el.querySelector('i')

		if ( ico ) {
			ico.className = ico.className.split(' ').filter(cls => !cls.startsWith('bi-') && cls != 'rotating').join(' ')
			ico.classList.add( icon )
			ico.classList.remove( 'rotating' )
		}
		let sp = this.el.querySelector('span')
		sp.textContent = `${txt}`

		// Add error background class
		this.el.classList.remove( 'info', 'success', 'warning' )
		this.el.classList.add( 'error' )

		this.close( timeout )
	}
}


function notify( msg, typ = 'info', timeout = 3000 )
{
	let n = new Notice( msg, typ )
	n.run( timeout )
}

notify.load = function( msg, typ, ico ){
	if ( !typ ) typ = 'info'
	if ( !ico ) ico = 'bi-arrow-clockwise'
	return new Notice( msg, typ, ico )
}
notify.erro = function( msg, typ, ico ){
	if ( !typ ) typ = 'error'
	if ( !ico ) ico = 'bi-x-circle-fill'
	return new Notice( msg, typ, ico )
}

