
//========================================================================
// Auto Selection
//========================================================================
function _groupByMuodId(assets){
	const groups = {}
	for ( const ass of assets){
		const gid = ass.vw?.muodId ?? ass.autoId
		if (!groups[gid]) groups[gid] = []
		groups[gid].push(ass)
	}
	return groups
}

function _checkLivePhoto(grpAssets, ausl){
	if (!ausl?.allLive) return []
	const liveIds = []
	for ( const ass of grpAssets){
		if (ass.vdoId || ass.pathVdo) liveIds.push(ass.autoId)
	}
	return liveIds
}

function _shouldSkipLowSim(grpAssets, ausl){
	if (!ausl?.skipLow) return false
	for ( const ass of grpAssets){
		const scr = ass.vw?.score
		if (scr && scr !== 0 && scr <= 0.96) return true
	}
	return false
}

function _countExif(exif){
	if (!exif) return 0
	const fields = [
		'dateTimeOriginal', 'modifyDate', 'make', 'model', 'lensModel',
		'fNumber', 'focalLength', 'exposureTime', 'iso',
		'latitude', 'longitude', 'city', 'state', 'country', 'description',
		'exifImageWidth', 'exifImageHeight', 'fileSizeInByte'
	]
	return fields.filter(f => exif[f] != null).length
}

function _normalizeDate(dt){
	if (!dt) return ''
	const s = String(dt)
	if (s.includes('.') && (s.includes('+') || s.endsWith('Z'))) {
		const beforeDot = s.split('.')[0]
		if (s.includes('+')) return beforeDot + '+' + s.split('+').pop()
		if (s.endsWith('Z')) return beforeDot + 'Z'
	}
	return s
}

function _selectBestAsset(grpAssets, ausl){
	if (!grpAssets?.length) return null

	const metrics = grpAssets.map(ass =>{
		const exif = ass.jsonExif
		const dt = exif?.dateTimeOriginal || ass.fileCreatedAt
		return {
			aid: ass.autoId,
			dt: _normalizeDate(dt),
			exfCnt: _countExif(exif),
			fileSz: exif?.fileSizeInByte || 0,
			dim: (exif?.exifImageWidth || 0) + (exif?.exifImageHeight || 0),
			nameLen: ass.originalFileName?.length || 0,
			fileType: ass.originalFileName?.toLowerCase().split('.').pop() || '',
			isFav: !!ass.isFavorite,
			hasAlb: !!(ass.ex?.albs?.length),
			ownerId: ass.ownerId || '',
			path: ass.originalPath || ''
		}
	})

	console.log(`[ausl] Group comparison:`)
	for ( const m of metrics){
		console.log(`[ausl]   #${m.aid}: date[${m.dt}] exif[${m.exfCnt}] fsize[${m.fileSz}] dim[${m.dim}] name[${m.nameLen}] type[${m.fileType}] fav[${m.isFav}] alb[${m.hasAlb}] owner[${m.ownerId?.slice(0, 8) || ''}] path[${m.path?.slice(-30) || ''}]`)
	}

	const add = (idx, vals, isMax, weight, label) =>{
		if (weight <= 0) return {pts: 0, reason: null}
		const uniq = [...new Set(vals)]
		if (uniq.length <= 1) return {pts: 0, reason: null}
		const target = isMax ? Math.max(...vals) : Math.min(...vals)
		if (vals[idx] === target) {
			const pts = weight * 10
			return {pts, reason: `${label}+${pts}`}
		}
		return {pts: 0, reason: null}
	}

	let bestAid = null, bestScr = -1, bestReasons = []
	const allScores = {} // { aid: { score, reasons } }

	for ( let i = 0; i < grpAssets.length; i++ ){
		let scr = 0
		const reasons = []
		const m = metrics[i]

		// DateTime
		const dates = metrics.map(x => x.dt).filter(d => d)
		if (m.dt && dates.length > 1 && new Set(dates).size > 1) {
			const sorted = [...dates].sort()
			if (ausl.earlier > 0 && m.dt === sorted[0]) {
				const pts = ausl.earlier * 10
				scr += pts
				reasons.push(`Earlier+${pts}`)
			}
			if (ausl.later > 0 && m.dt === sorted[sorted.length - 1]) {
				const pts = ausl.later * 10
				scr += pts
				reasons.push(`Later+${pts}`)
			}
		}

		let r
		r = add(i, metrics.map(x => x.exfCnt), true, ausl.exRich, 'ExifRich')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.exfCnt), false, ausl.exPoor, 'ExifPoor')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.fileSz), true, ausl.ofsBig, 'BigSize')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.fileSz), false, ausl.ofsSml, 'SmallSize')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.dim), true, ausl.dimBig, 'BigDim')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.dim), false, ausl.dimSml, 'SmallDim')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.nameLen), true, ausl.namLon, 'LongName')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}
		r = add(i, metrics.map(x => x.nameLen), false, ausl.namSht, 'ShortName')
		if (r.pts) {scr += r.pts; reasons.push(r.reason)}

		// File type
		if (ausl.typJpg > 0 && ['jpg', 'jpeg'].includes(m.fileType)) {
			const pts = ausl.typJpg * 10
			scr += pts
			reasons.push(`JPG+${pts}`)
		}
		if (ausl.typPng > 0 && m.fileType === 'png') {
			const pts = ausl.typPng * 10
			scr += pts
			reasons.push(`PNG+${pts}`)
		}
		if (ausl.typHeic > 0 && ['heic', 'heif'].includes(m.fileType)) {
			const pts = ausl.typHeic * 10
			scr += pts
			reasons.push(`HEIC+${pts}`)
		}

		// Immich
		if (ausl.fav > 0 && m.isFav) {
			const pts = ausl.fav * 10
			scr += pts
			reasons.push(`Fav+${pts}`)
		}
		if (ausl.inAlb > 0 && m.hasAlb) {
			const pts = ausl.inAlb * 10
			scr += pts
			reasons.push(`InAlb+${pts}`)
		}

		// User & Path
		if (ausl.usr?.v > 0 && ausl.usr?.k && m.ownerId === ausl.usr.k) {
			const pts = ausl.usr.v * 10
			scr += pts
			reasons.push(`Owner+${pts}`)
		}
		if (ausl.pth?.v > 0 && ausl.pth?.k && m.path.includes(ausl.pth.k)) {
			const pts = ausl.pth.v * 10
			scr += pts
			reasons.push(`Path+${pts}`)
		}

		allScores[m.aid] = {score: scr, reasons}
		console.log(`[ausl] #${m.aid}: score[${scr}] (${reasons.length ? reasons.join(', ') : 'no matches'})`)

		if (scr > bestScr) {
			bestScr = scr
			bestAid = m.aid
			bestReasons = reasons
		}
	}

	if (bestAid) console.log(`[ausl] Winner: #${bestAid} score[${bestScr}] (${bestReasons.join(', ')})`)

	return {aid: bestAid, score: bestScr, reasons: bestReasons, allScores}
}

window.autoSelectReasons = {}

let _lastAutoSelSig = null
function getAutoSelSig(assets, ausl){
	const assSig = assets?.map(a => a.autoId).sort((a,b) => a - b).join(',') || ''
	const auslSig = JSON.stringify(ausl || {})
	return `${assSig}|${auslSig}`
}

function getAutoSelectAuids(assets, ausl){
	console.log(`[ausl] Starting auto-selection, ausl.on[${ausl?.on}], assets count=${assets?.length || 0}`)
	console.log(`[ausl] Weights: Earlier[${ausl?.earlier}] Later[${ausl?.later}] ExifRich[${ausl?.exRich}] ExifPoor[${ausl?.exPoor}] BigSize[${ausl?.ofsBig}] SmallSize[${ausl?.ofsSml}] BigDim[${ausl?.dimBig}] SmallDim[${ausl?.dimSml}] SkipLow[${ausl?.skipLow}] AllLive[${ausl?.allLive}] JPG[${ausl?.typJpg}] PNG[${ausl?.typPng}] HEIC[${ausl?.typHeic}] Fav[${ausl?.fav}] InAlb[${ausl?.inAlb}] User[${ausl?.usr?.k}:${ausl?.usr?.v}] Path[${ausl?.pth?.k}:${ausl?.pth?.v}]`)

	window.autoSelectReasons = {}

	if (!ausl?.on || !assets?.length) return []

	const hasActive = ausl.earlier > 0 || ausl.later > 0 || ausl.exRich > 0 || ausl.exPoor > 0 || ausl.ofsBig > 0 || ausl.ofsSml > 0 || ausl.dimBig > 0 || ausl.dimSml > 0 || ausl.namLon > 0 || ausl.namSht > 0 || ausl.typJpg > 0 || ausl.typPng > 0 || ausl.typHeic > 0 || ausl.fav > 0 || ausl.inAlb > 0 || ausl.usr?.v > 0 || ausl.pth?.v > 0

	if (!hasActive) {
		console.log(`[ausl] No active weights, skipping`)
		return []
	}

	const groups = _groupByMuodId(assets)
	console.log(`[ausl] Grouped ${assets.length} assets into ${Object.keys(groups).length} groups`)

	const selIds = []

	for ( const [gid, grpAss] of Object.entries(groups) ){
		console.log(`[ausl] Processing group ${gid} with ${grpAss.length} assets: [${grpAss.map(a => a.autoId).join(', ')}]`)

		const liveIds = _checkLivePhoto(grpAss, ausl)
		if (liveIds.length) {
			console.log(`[ausl] Group ${gid}: Selected ALL LivePhoto assets [${liveIds.join(', ')}]`)
			for ( const lid of liveIds ) window.autoSelectReasons[lid] = ['LivePhoto']
			selIds.push(...liveIds)
			continue
		}

		if (_shouldSkipLowSim(grpAss, ausl)) {
			console.log(`[ausl] Group ${gid}: SKIPPING due to low similarity`)
			continue
		}

		const result = _selectBestAsset(grpAss, ausl)
		if (result?.aid) {
			selIds.push(result.aid)
			window.autoSelectReasons[result.aid] = result.reasons
			console.log(`[ausl] Group ${gid}: Selected best asset #${result.aid}`)
		}
	}

	console.log(`[ausl] Final selection: ${selIds.length} assets: [${selIds.join(', ')}]`)
	return selIds
}

//========================================================================
// Auto-Select Tooltip UI
//========================================================================
function updateAutoSelectTips(){
	// Remove existing tips
	document.querySelectorAll('.ausl-tip').forEach(el => el.remove())

	const reasons = window.autoSelectReasons || {}
	if (!Object.keys(reasons).length) return

	for ( const [aid, reasonList] of Object.entries(reasons) ){
		const card = getCardById(aid)
		if (!card) continue

		const label = card.querySelector('label')
		if (!label) continue

		// Check if tip already exists
		if (label.querySelector('.ausl-tip')) continue

		const tipText = reasonList.join(', ')
		const tip = document.createElement('span')
		tip.className = 'ausl-tip'
		tip.textContent = 'Auto-Selected ？ '
		tip.setAttribute('data-tip', tipText)
		label.appendChild(tip)
	}

	console.log(`[ausl] Updated ${Object.keys(reasons).length} tooltip(s)`)
}

//========================================================================
// Card helpers
//========================================================================
function getCardById(targetId){
	const cards = document.querySelectorAll(`[id*='"type":"card-select"']`)
	// console.log(`[getCardById] Looking for targetId: ${targetId} (type: ${typeof targetId}), found ${cards.length} cards`)

	for ( const cd of cards){
		try {
			const idAttr = JSON.parse(cd.id)
			const cardId = parseInt(idAttr.id)
			const searchId = parseInt(targetId)

			// console.log(`[getCardById] Checking card: cardId=${cardId} (type: ${typeof cardId}), searchId=${searchId} (type: ${typeof searchId}), type=${idAttr.type}`)
			if (cardId == searchId && idAttr.type == 'card-select') {
				// console.log(`[getCardById] Found matching card for ID: ${targetId}`
				return cd
			}
		}
		catch (e){
			console.error('Error parsing ID attribute:', cd.id, e)
		}
	}
	console.warn(`[getCardById] No card found for targetId: ${targetId}`)
	return null // Card not found
}



//------------------------------------------------------------------------
// similar
//------------------------------------------------------------------------
window.dash_clientside.similar = {

	onCardSelectClicked(){
		if (dash_clientside.callback_context.triggered.length > 0) {
			let triggered = dash_clientside.callback_context.triggered[0]
			if (triggered.prop_id && triggered.value > 0) {
				let triggeredId = JSON.parse(triggered.prop_id.split('.')[0])
				Ste.toggle(triggeredId.id)

				let steData = {
					cntTotal: Ste.cntTotal,
					selectedIds: Array.from(Ste.selectedIds),
				}

				console.log('[Ste] Syncing to ste store on selection:', steData)
				return steData
			}
		}
		return dash_clientside.no_update
	},

	onSimJs(now_data, ste_data, sets_data){
		const triggered = dash_clientside.callback_context.triggered
		const propId = triggered?.[0]?.prop_id
		if (triggered?.length > 0) {
			if (propId === 'store-state.data') {
				console.log('[Ste] Skip: triggered by ste store (selection click)')
				return dash_clientside.no_update
			}
		}

		const assets = now_data?.sim?.assCur
		const ausl = sets_data?.ausl
		const curSig = getAutoSelSig(assets, ausl)
		if (curSig === _lastAutoSelSig) {
			console.log('[ausl] Skip: assets & ausl unchanged')
			return dash_clientside.no_update
		}
		_lastAutoSelSig = curSig
		console.log(`[NowSync] ==================== triggered[${JSON.stringify(triggered)}] =====================`)

		if (assets) {
			if (Ste) {
				Ste.initSilent(assets.length)
				Ste.selectedIds.clear()

				const autoSelectedIds = getAutoSelectAuids(assets, ausl)

				for ( const autoId of autoSelectedIds ) Ste.selectedIds.add(autoId)

				setTimeout(() =>{
					const cards = document.querySelectorAll(`[id*='"type":"card-select"']`)
					if (cards.length > 0) {
						Ste.updAllCss()
						Ste.updBtns()
						updateAutoSelectTips()
						dsh.syncSte(Ste.cntTotal, Ste.selectedIds)
						if (autoSelectedIds.length > 0) notify(`[Auto Selection] selected ${autoSelectedIds.length} items`, 'success')
						console.log(`[Ste] Auto-selected ${autoSelectedIds.length} items`)
					}
					else {
						setTimeout(() =>{
							Ste.updAllCss()
							Ste.updBtns()
							updateAutoSelectTips()
							dsh.syncSte(Ste.cntTotal, Ste.selectedIds)
							console.log(`[Ste] Retry: auto-selected ${autoSelectedIds.length} items`)
						}, 200)
					}
				}, 300)
			}
		}
		return dash_clientside.no_update
	}
}



//------------------------------------------------------------------------
// Group assets by their visual groups in Similar View
//------------------------------------------------------------------------
function groupAssetsByVisualGroups(data){
	const groups = []
	let currentGroupId = 1

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

	children.forEach(child =>{
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
				}
				catch (e){
					console.error('[Export] Error parsing group asset meta:', e)
				}
			}
		}
	})

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
window.exportIdsToCSV = function exportIdsToCSV(){
	try {
		const cards = document.querySelectorAll('.card-meta')

		if (cards.length === 0) {
			alert('No images found to export')
			return
		}

		// Extract data from each meta element
		const data = []
		cards.forEach(metaDiv =>{
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
					}
					catch (e){
						console.error('[Export] Error parsing meta data:', e, 'Raw data:', metaDiv.dataset.meta)
					}
				} else {
					console.warn('[Export] No meta data in dataset')
				}
			}
			catch (e){
				console.error('[Export] Error extracting data from meta element:', e)
			}
		})


		if (data.length === 0) {
			alert('No data could be extracted')
			return
		}

		const isGroupedView = window.location.pathname.includes('/similar')
		let exportData

		if (isGroupedView) {
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

		const jsonContent = JSON.stringify(exportData, null, 2)

		const blob = new Blob([jsonContent], {type: 'application/json;charset=utf-8;'})
		const link = document.createElement('a')
		const url = URL.createObjectURL(blob)

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
	}
	catch (e){
		console.error('[Export] Error exporting IDs:', e)
		alert('Error exporting IDs: ' + e.message)
	}
}



//------------------------------------------------------------------------
// Tab Acts Floating Bar
//------------------------------------------------------------------------
function initTabActsFloating(){
	const tabActs = document.querySelector('.tab-acts')
	if (!tabActs) return

	let placeholder = document.createElement('div')
	placeholder.className = 'tab-acts-placeholder'
	tabActs.parentNode.insertBefore(placeholder, tabActs.nextSibling)

	let originalTop = null
	let isFloating = false

	function updateOriginalTop(){
		if (!isFloating) {
			const rect = tabActs.getBoundingClientRect()
			originalTop = rect.top + window.scrollY
		}
	}

	function toggleFloatingBar(){
		const currentTab = document.querySelector('.nav-tabs .nav-link.active')
		const isCurrentTab = currentTab && currentTab.textContent.trim() == 'current'
		const scrollY = window.scrollY

		if (!isCurrentTab) {
			if (isFloating) {
				tabActs.classList.remove('floating', 'show')
				placeholder.classList.remove('active')
				isFloating = false
			}
			return
		}

		if (originalTop === null) updateOriginalTop()

		const shouldFloat = scrollY > originalTop + 50

		if (shouldFloat !== isFloating) {
			if (shouldFloat) {
				tabActs.classList.add('floating')
				placeholder.classList.add('active')
				setTimeout(() => tabActs.classList.add('show'), 10)
				isFloating = true
			}
			else {
				tabActs.classList.remove('show')
				setTimeout(() =>{
					tabActs.classList.remove('floating')
					placeholder.classList.remove('active')
				}, 300)
				isFloating = false
			}
		}
	}

	window.addEventListener('scroll', toggleFloatingBar)
	window.addEventListener('resize', () =>{
		originalTop = null
		updateOriginalTop()
	})

	document.addEventListener('click', function(e){
		if (e.target && e.target.matches('.nav-link')) {
			setTimeout(() =>{
				originalTop = null
				updateOriginalTop()
				toggleFloatingBar()
			}, 100)
		}
	})

	updateOriginalTop()
	setTimeout(toggleFloatingBar, 100)
}

//------------------------------------------------------------------------
// Goto Top Button
//------------------------------------------------------------------------
function initBtnTop(btn){

	function toggleGotoTopBtn(){
		const currentTab = document.querySelector('.nav-tabs .nav-link.active')
		const isCurrentTab = currentTab && currentTab.textContent.trim() == 'current'
		const scrollY = window.scrollY

		// console.log('[GotoTop] Toggle check - isCurrentTab:', isCurrentTab, 'scrollY:', scrollY)

		if (isCurrentTab && scrollY > 200) {
			btn.classList.add('show')
			btn.style.display = 'block'
		}
		else {
			btn.classList.remove('show')
		}
	}

	function scrollToTop(){
		const dst = document.querySelector('#sim-btn-fnd')

		if (dst) {
			dst.scrollIntoView({behavior: 'smooth', block: 'start'})
		}
		else {
			// console.warn('[GotoTop] Tab acts element not found, scrolling to top')
			window.scrollTo({top: 0, behavior: 'smooth'})
		}
	}

	window.addEventListener('scroll', toggleGotoTopBtn)
	btn.addEventListener('click', scrollToTop)

	document.addEventListener('click', function(e){if (e.target && e.target.matches('.nav-link')) setTimeout(toggleGotoTopBtn, 100)})

	toggleGotoTopBtn()
}



document.addEventListener('DOMContentLoaded', function(){

	//------------------------------------------------------------------------
	// for pages
	//------------------------------------------------------------------------
	ui.mob.waitFor('.tab-acts', initTabActsFloating)
	ui.mob.waitFor('#sim-goto-top-btn', initBtnTop)

})
