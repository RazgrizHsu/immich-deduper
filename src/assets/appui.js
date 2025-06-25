const ui = window.ui = {

	mob:{
		waitFor( selector, callback, logPrefix )
		{
			const dst = document.querySelector( selector )
			const log = typeof logPrefix == 'string' && logPrefix.length > 0

			if ( dst )
			{
				if ( log ) console.log( `${logPrefix} Found element:`, dst )
				callback( dst )
			}
			else
			{
				if ( log ) console.log( `${logPrefix} Element not found, initializing observer for ${selector}` )
				const observer = new MutationObserver( function()
				{
					const dst = document.querySelector( selector )
					if ( dst )
					{
						if ( log ) console.log( `${logPrefix} Element found via observer:`, dst )
						observer.disconnect()
						callback( dst )
					}
				} )
				observer.observe( document.body, { childList: true, subtree: true } )
			}
		}
	}
}



//========================================================================
// global
//========================================================================
document.addEventListener( 'DOMContentLoaded', () => {
	const root = document.body

	function bindEvts()
	{
		const sps = document.querySelectorAll( 'span[class*="tag"]' )
		sps.forEach( span => {
			if ( span._hoverEventsBound ) return
			span.addEventListener( 'mouseenter', function(){
				this.style.opacity = '0.6'
				this.style.transition = 'opacity 0.3s ease'
				this.style.cursor = 'pointer'
			} )

			span.addEventListener( 'mouseleave', function(){
				this.style.opacity = '1'
				this.style.transition = 'opacity 0.3s ease'
				this.style.cursor = 'default'
			} )
			span._hoverEventsBound = true
		} )
	}

	bindEvts()

	const obs = new MutationObserver( muts => {
		muts.forEach( mutation => { if ( mutation.type == 'childList' ) bindEvts() } )
	} )

	obs.observe( root, { childList: true, subtree: true } )


	root.addEventListener( 'click', async ( event ) => {
		const dst = event.target

		const span = dst.closest( 'span[class*="tag"]' )
		if ( span )
		{
			const textToCopy = span.textContent

			if ( navigator.clipboard && navigator.clipboard.writeText )
			{
				try
				{
					await navigator.clipboard.writeText( textToCopy )
					console.log( 'copy: ' + textToCopy )
					notify( `copy! ${ textToCopy }` )
				}
				catch ( err )
				{
					console.error( 'copy failed', err )
				}
			}
			else
			{
				console.warn( 'Not support Clipboard API' )
				const tempInput = document.createElement( 'textarea' )
				tempInput.value = textToCopy
				document.body.appendChild( tempInput )
				tempInput.select()
				try
				{
					document.execCommand( 'copy' )

					notify( `copy! ${ textToCopy }` )
					console.log( 'copy!(old) ' + textToCopy )
				}
				catch ( err )
				{
					console.error( 'copy(old) failed', err )
				}
				document.body.removeChild( tempInput )
			}
		}
	} )
} )
