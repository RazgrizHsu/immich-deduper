
const Ste = window.Ste = {
	cntTotal: 0,
	selectedIds: new Set(),
	_lastSyncHash: null,

	init( cnt )
	{
		this.cntTotal = cnt
		this.selectedIds.clear()
		console.log( `[Ste] Initialized with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )

		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	initSilent( cnt )
	{
		this.cntTotal = cnt
		this.selectedIds.clear()
		console.log( `[Ste] Silent init with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )
	},

	toggle( aid )
	{
		this.selectedIds.has( aid ) ? this.selectedIds.delete( aid ) : this.selectedIds.add( aid )

		console.log( `[Ste] Toggled ${ aid }, selected count: ${ this.selectedIds.size }` )

		this.updCss( aid )
		this.updBtns()
	},

	updCss( aid )
	{
		// console.log( `[Ste] updCss called for aid: ${aid} (type: ${typeof aid})` )

		let card = getCardById( aid )
		if ( !card )
		{
			console.error( `[Ste] No cards found for ${ aid }` )

			const allCards = document.querySelectorAll( `[id*='"type":"card-select"']` )
			console.log( `[Ste] Available cards:` )
			allCards.forEach( ( c, idx ) => {
				try
				{
					const idAttr = JSON.parse( c.id )
					console.log( `[Ste] Card[${ idx }] id[${ idAttr.id }] (type: ${ typeof idAttr.id }), type=${ idAttr.type }` )
				}
				catch ( e )
				{
					console.log( `[Ste] Card ${ idx }: parse error for ${ c.id }` )
				}
			} )
			return
		}

		const par = card.closest( '.card' )
		const cbx = card.querySelector( 'input[type="checkbox"]' )
		const isSelected = this.selectedIds.has( aid )

		// console.log( `[Ste] updCss ${aid}: isSelected[${isSelected}], parentCard[${!!par}], checkbox[${!!cbx}]` )

		if ( !par ) console.error( `[updCss] not found aid[${ aid }] card` )

		if ( par )
		{
			par.classList[ isSelected ? 'add' : 'remove' ]( 'checked' )
			// console.log( `[Ste:updCss] Updated card ${aid} visual state: ${isSelected ? 'checked' : 'unchecked'}` )
		}

		if ( cbx ) cbx.checked = isSelected
	},

	updBtns()
	{
		const cntSel = this.selectedIds.size
		const cntAll = this.cntTotal
		const cntDiff = cntAll - cntSel

		const btnRm = document.getElementById( 'sim-btn-RmSel' )
		const btnRS = document.getElementById( 'sim-btn-OkSel' )
		const btnAllSelect = document.getElementById( 'sim-btn-AllSelect' )
		const btnAllCancel = document.getElementById( 'sim-btn-AllCancel' )

		if ( btnRm ) btnRm.textContent = `❌ Delete selected ( ${ cntSel } ) and ✅ Keep others( ${ cntDiff } )`
		if ( btnRS ) btnRS.textContent = `✅ Keep selected ( ${ cntSel } ) and ❌ delete others( ${ cntDiff } )`

		if ( btnAllSelect ) btnAllSelect.disabled = ( cntSel >= cntAll || cntAll == 0 )
		if ( btnAllCancel ) btnAllCancel.disabled = ( cntSel == 0 )

		console.log( `[Ste] updBtns - selected[ ${ cntSel } / ${ cntAll } ]` )
	},

	selectAll()
	{
		const cards = document.querySelectorAll( '[id*="card-select"]' )
		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) this.selectedIds.add( assetId )
		} )
		this.updAllCss()
		this.updBtns()
		console.log( `[Ste] Selected all ${ this.selectedIds.size } assets` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	clearAll()
	{
		this.selectedIds.clear()
		this.updAllCss()
		this.updBtns()
		console.log( `[Ste] Cleared all selections` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	updAllCss()
	{
		const cards = document.querySelectorAll( '[id*="card-select"]' )
		console.log( `[Ste] updAllCss cards[ ${ cards.length } ]` )
		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) this.updCss( assetId )
		} )
	},

	extractAssetIdBy( elem )
	{
		try
		{
			const idStr = elem.getAttribute( 'id' )
			if ( idStr && idStr.includes( 'card-select' ) )
			{
				const match = idStr.match( /"id":(\d+)/ )
				return match ? parseInt( match[ 1 ] ) : null // Return number instead of string
			}
		}
		catch ( e )
		{ console.error( '[Ste] Error extracting asset ID:', e ) }
		return null
	},

	getGroupCards( groupId )
	{
		const cards = []
		const gv = document.querySelector( '.gv' )

		if ( !gv )
		{
			console.warn( `[Ste] No .gv container found` )
			return cards
		}

		const chs = Array.from( gv.children )
		let collecting = false

		chs.forEach( child => {
			if ( child.classList.contains( 'hr' ) )
			{
				const label = child.querySelector( 'label' )
				if ( label )
				{
					const match = label.textContent.match( /Group (\d+)/ )
					if ( match )
					{
						let gid = parseInt( match[ 1 ] )
						collecting = ( gid == groupId )
					}
				}
			}
			else if ( collecting )
			{
				const cardSelect = child.querySelector( '[id*="card-select"]' )
				if ( cardSelect )
				{
					cards.push( cardSelect )
				}
				else
				{
					collecting = false
				}
			}
		} )

		console.log( `[Ste] Found ${ cards.length } cards for group ${ groupId }` )
		return cards
	},

	selectGroup( groupId )
	{
		const grps = this.getGroupCards( groupId )
		let cnt = 0

		grps.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId && !this.selectedIds.has( assetId ) )
			{
				this.selectedIds.add( assetId )
				this.updCss( assetId )
				cnt++
			}
		} )

		this.updBtns()
		console.log( `[Ste] Selected ${ cnt } items in group ${ groupId }` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	clearGroup( groupId )
	{
		const cards = this.getGroupCards( groupId )
		let deselectedCount = 0

		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId && this.selectedIds.has( assetId ) )
			{
				this.selectedIds.delete( assetId )
				this.updCss( assetId )
				deselectedCount++
			}
		} )

		this.updBtns()
		console.log( `[Ste] Deselected ${ deselectedCount } items in group ${ groupId }` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},
}

document.addEventListener( 'DOMContentLoaded', function(){

	//------------------------------------------------
	document.addEventListener( 'click', function( event ){

		const ste = Ste

		//------------------------------------------------------
		// acts: cbx select status
		//------------------------------------------------------
		if ( event.target.id == 'sim-btn-AllSelect' )
		{
			event.preventDefault()
			if ( ste ) ste.selectAll()
		}
		if ( event.target.id == 'sim-btn-AllCancel' )
		{
			event.preventDefault()
			if ( ste ) ste.clearAll()
		}

		//------------------------------------------------------
		// group selection
		//------------------------------------------------------
		if ( event.target.id && event.target.id.startsWith( 'cbx-sel-grp-all-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'cbx-sel-grp-all-', '' )
			if ( ste ) ste.selectGroup( groupId )
		}
		if ( event.target.id && event.target.id.startsWith( 'cbx-sel-grp-non-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'cbx-sel-grp-non-', '' )
			if ( ste ) ste.clearGroup( groupId )
		}

		//------------------------------------------------------
		//
		//------------------------------------------------------

	} )

} )
