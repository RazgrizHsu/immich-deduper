
//------------------------------------------------------------------------
// TaskPanel Auto Hide on Scroll
//------------------------------------------------------------------------
function initTaskPanelAutoHide()
{
	function onScroll()
	{
		const pal = document.querySelector( '.tskPanel.fly' )
		if ( !pal ) return
		pal.classList.remove( 'fly' )
	}

	window.addEventListener( 'scroll', onScroll )
}

document.addEventListener( 'DOMContentLoaded', function(){

	initTaskPanelAutoHide()
} )
