
function getCardById( targetId )
{
	const cards = document.querySelectorAll( `[id*='"type":"card-select"']` )
	// console.log(`[getCardById] Looking for targetId: ${targetId} (type: ${typeof targetId}), found ${cards.length} cards`)

	for ( const cd of cards )
	{
		try
		{
			const idAttr = JSON.parse( cd.id )
			const cardId = parseInt( idAttr.id )
			const searchId = parseInt( targetId )

			// console.log(`[getCardById] Checking card: cardId=${cardId} (type: ${typeof cardId}), searchId=${searchId} (type: ${typeof searchId}), type=${idAttr.type}`)
			if ( cardId == searchId && idAttr.type == "card-select" )
			{
				// console.log(`[getCardById] Found matching card for ID: ${targetId}`
				return cd
			}
		}
		catch ( e )
		{
			console.error( "Error parsing ID attribute:", cd.id, e )
		}
	}
	console.warn( `[getCardById] No card found for targetId: ${ targetId }` )
	return null // Card not found
}



//------------------------------------------------------------------------
// similar
//------------------------------------------------------------------------
window.dash_clientside.similar = {

	onCardSelectClicked()
	{
		if ( dash_clientside.callback_context.triggered.length > 0 )
		{
			let triggered = dash_clientside.callback_context.triggered[ 0 ]
			if ( triggered.prop_id && triggered.value > 0 )
			{
				let triggeredId = JSON.parse( triggered.prop_id.split( '.' )[ 0 ] )
				Ste.toggle( triggeredId.id )

				let steData = {
					cntTotal: Ste.cntTotal,
					selectedIds: Array.from( Ste.selectedIds ),
				}

				console.log( '[Ste] Syncing to ste store on selection:', steData )
				return steData
			}
		}
		return dash_clientside.no_update
	},

	onNowSyncToDummyInit( now_data, ste_data )
	{
		if ( now_data && now_data.sim && now_data.sim.assCur )
		{
			let assets = now_data.sim.assCur
			if ( Ste )
			{
				const selectedIdsArray = ste_data && ste_data.selectedIds ? ste_data.selectedIds : []
				const syncHash = `${ assets.length }-${ selectedIdsArray.join( ',' ) }`

				if ( Ste._lastSyncHash == syncHash )
				{
					console.log( `[Ste] Skipping duplicate sync for hash: ${ syncHash }` )
					return dash_clientside.no_update
				}

				Ste._lastSyncHash = syncHash

				Ste.initSilent( assets.length )

				// Sync initial selection from ste store without triggering events
				if ( ste_data && ste_data.selectedIds && Array.isArray( ste_data.selectedIds ) )
				{
					for ( const autoId of ste_data.selectedIds ) Ste.selectedIds.add( autoId )

					setTimeout( () => {
						const cards = document.querySelectorAll( `[id*='"type":"card-select"']` )
						if ( cards.length > 0 )
						{
							Ste.updAllCss()
							Ste.updBtns()
							console.log( `[Ste] Synced ${ ste_data.selectedIds.length } initial selections from server:`, ste_data.selectedIds )
						}
						else
						{
							console.log( `[Ste] Cards not ready, retrying in 200ms...` )
							setTimeout( () => {
								Ste.updAllCss()
								Ste.updBtns()
								console.log( `[Ste] Retry synced ${ ste_data.selectedIds.length } initial selections from server:`, ste_data.selectedIds )
							}, 200 )
						}
					}, 300 )
				}
				else
				{
					setTimeout( () => {
						Ste.updBtns()
						console.log( `[Ste] Initialized with ${ assets.length } assets, no initial selections` )
					}, 300 )
				}
			}
		}
		return dash_clientside.no_update
	}
}




//------------------------------------------------------------------------
// Group assets by their visual groups in Similar View
//------------------------------------------------------------------------
function groupAssetsByVisualGroups(data) {
	const groups = []
	let currentGroupId = 1

	// Find all group headers in the DOM
	const gvContainer = document.querySelector('.gv.fsp')
	if (!gvContainer) {
		// No groups found, return all assets as one group
		return [{
			group: 1,
			assets: data.map(item => ({
				assetId: item.assetId,
				autoId: parseInt(item.autoId),
				filename: item.filename,
				path: item.path
			}))
		}]
	}

	const children = Array.from(gvContainer.children)
	let currentGroupAssets = []

	children.forEach(child => {
		// Check if this is a group header
		if (child.classList.contains('hr')) {
			// Save previous group if it has assets
			if (currentGroupAssets.length > 0) {
				groups.push({
					group: currentGroupId,
					assets: currentGroupAssets
				})
				currentGroupAssets = []
				currentGroupId++
			}
		} else {
			// This should be an asset card
			const metaDiv = child.querySelector('.card-meta')
			if (metaDiv && metaDiv.dataset.meta) {
				try {
					const meta = JSON.parse(metaDiv.dataset.meta)
					currentGroupAssets.push({
						assetId: meta.id,
						autoId: parseInt(meta.autoId),
						filename: meta.originalFileName,
						path: meta.originalPath
					})
				} catch (e) {
					console.error('[Export] Error parsing group asset meta:', e)
				}
			}
		}
	})

	// Add the last group
	if (currentGroupAssets.length > 0) {
		groups.push({
			group: currentGroupId,
			assets: currentGroupAssets
		})
	}

	return groups
}

//------------------------------------------------------------------------
// Export IDs to JSON
//------------------------------------------------------------------------
window.exportIdsToCSV = function exportIdsToCSV()
{
	try {
		// Get all image cards that have meta data
		const cards = document.querySelectorAll('.card-meta')

		if (cards.length === 0) {
			alert('No images found to export')
			return
		}

		// Extract data from each meta element
		const data = []
		cards.forEach(metaDiv => {
			try {
				console.log('[Export] Processing metaDiv:', metaDiv.dataset)
				if (metaDiv.dataset.meta) {
					console.log('[Export] Meta data:', metaDiv.dataset.meta)
					try {
						const meta = JSON.parse(metaDiv.dataset.meta)
						console.log('[Export] Parsed meta:', meta)
						data.push({
							assetId: meta.id || '',
							autoId: meta.autoId || '',
							filename: meta.originalFileName || '',
							path: meta.originalPath || ''
						})
					} catch (e) {
						console.error('[Export] Error parsing meta data:', e, 'Raw data:', metaDiv.dataset.meta)
					}
				} else {
					console.warn('[Export] No meta data in dataset')
				}
			}
			catch (e) {
				console.error('[Export] Error extracting data from meta element:', e)
			}
		})


		if (data.length === 0) {
			alert('No data could be extracted')
			return
		}

		// Check if we're in Similar View to create grouped structure
		const isGroupedView = window.location.pathname.includes('/similar')
		let exportData

		if (isGroupedView) {
			// Group assets by their visual groups in Similar View
			exportData = groupAssetsByVisualGroups(data)
		} else {
			// For View page, just export as flat array
			exportData = data.map(item => ({
				assetId: item.assetId,
				autoId: parseInt(item.autoId),
				filename: item.filename,
				path: item.path
			}))
		}

		// Create JSON content
		const jsonContent = JSON.stringify(exportData, null, 2)

		// Create download link
		const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
		const link = document.createElement('a')
		const url = URL.createObjectURL(blob)

		// Generate filename with timestamp
		const now = new Date()
		const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, -5)
		const fileType = isGroupedView ? 'groups' : 'assets'
		link.setAttribute('href', url)
		link.setAttribute('download', `immich_${fileType}_${timestamp}.json`)
		link.style.visibility = 'hidden'

		document.body.appendChild(link)
		link.click()
		document.body.removeChild(link)

		const message = isGroupedView ?
			`Exported ${exportData.length} groups with ${data.length} total assets` :
			`Exported ${data.length} assets`
		alert(`${message} to JSON file`)
	} catch (e) {
		console.error('[Export] Error exporting IDs:', e)
		alert('Error exporting IDs: ' + e.message)
	}
}



//------------------------------------------------------------------------
// Tab Acts Floating Bar
//------------------------------------------------------------------------
function initTabActsFloating()
{
	const tabActs = document.querySelector( '.tab-acts' )
	if ( !tabActs ) return

	let placeholder = document.createElement( 'div' )
	placeholder.className = 'tab-acts-placeholder'
	tabActs.parentNode.insertBefore( placeholder, tabActs.nextSibling )

	let originalTop = null
	let isFloating = false

	function updateOriginalTop()
	{
		if ( !isFloating )
		{
			const rect = tabActs.getBoundingClientRect()
			originalTop = rect.top + window.scrollY
		}
	}

	function toggleFloatingBar()
	{
		const currentTab = document.querySelector( '.nav-tabs .nav-link.active' )
		const isCurrentTab = currentTab && currentTab.textContent.trim() == 'current'
		const scrollY = window.scrollY

		if ( !isCurrentTab )
		{
			if ( isFloating )
			{
				tabActs.classList.remove( 'floating', 'show' )
				placeholder.classList.remove( 'active' )
				isFloating = false
			}
			return
		}

		if ( originalTop === null ) updateOriginalTop()

		const shouldFloat = scrollY > originalTop + 50

		if ( shouldFloat !== isFloating )
		{
			if ( shouldFloat )
			{
				tabActs.classList.add( 'floating' )
				placeholder.classList.add( 'active' )
				setTimeout( () => tabActs.classList.add( 'show' ), 10 )
				isFloating = true
			}
			else
			{
				tabActs.classList.remove( 'show' )
				setTimeout( () => {
					tabActs.classList.remove( 'floating' )
					placeholder.classList.remove( 'active' )
				}, 300 )
				isFloating = false
			}
		}
	}

	window.addEventListener( 'scroll', toggleFloatingBar )
	window.addEventListener( 'resize', () => {
		originalTop = null
		updateOriginalTop()
	} )

	document.addEventListener( 'click', function( e ){
		if ( e.target && e.target.matches( '.nav-link' ) )
		{
			setTimeout( () => {
				originalTop = null
				updateOriginalTop()
				toggleFloatingBar()
			}, 100 )
		}
	} )

	updateOriginalTop()
	setTimeout( toggleFloatingBar, 100 )
}

//------------------------------------------------------------------------
// Goto Top Button
//------------------------------------------------------------------------
function initBtnTop( btn )
{

	function toggleGotoTopBtn()
	{
		const currentTab = document.querySelector( '.nav-tabs .nav-link.active' )
		const isCurrentTab = currentTab && currentTab.textContent.trim() == 'current'
		const scrollY = window.scrollY

		// console.log('[GotoTop] Toggle check - isCurrentTab:', isCurrentTab, 'scrollY:', scrollY)

		if ( isCurrentTab && scrollY > 200 )
		{
			btn.classList.add( 'show' )
			btn.style.display = 'block'
		}
		else
		{
			btn.classList.remove( 'show' )
		}
	}

	function scrollToTop()
	{
		const dst = document.querySelector( '#sim-btn-fnd' )

		if ( dst )
		{
			dst.scrollIntoView( { behavior: 'smooth', block: 'start' } )
		}
		else
		{
			// console.warn('[GotoTop] Tab acts element not found, scrolling to top')
			window.scrollTo( { top: 0, behavior: 'smooth' } )
		}
	}

	window.addEventListener( 'scroll', toggleGotoTopBtn )
	btn.addEventListener( 'click', scrollToTop )

	document.addEventListener( 'click', function( e ){
		if ( e.target && e.target.matches( '.nav-link' ) ) setTimeout( toggleGotoTopBtn, 100 )
	} )

	// Initial check
	toggleGotoTopBtn()
}



document.addEventListener( 'DOMContentLoaded', function(){


	//------------------------------------------------------------------------
	// for pages
	//------------------------------------------------------------------------
	ui.mob.waitFor('.tab-acts', initTabActsFloating )
	ui.mob.waitFor('#sim-goto-top-btn', initBtnTop)


} )
