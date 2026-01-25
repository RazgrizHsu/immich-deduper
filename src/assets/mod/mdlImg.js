
//------------------------------------------------------------------------
// mdlImg Client State Manager
//------------------------------------------------------------------------
const MdlImg = window.MdlImg = {
	state: {
		mdl: null,
		now: null,
		ste: null
	},

	init(mdl, now, ste){
		this.state.mdl = mdl
		this.state.now = now
		this.state.ste = ste

		if (ste) console.info(`[mdlImg] init ste, cntTotal[ ${ste.cntTotal} ] selected( ${ste.selectedIds.length} )[ ${ste.selectedIds} ]`)
		return this
	},

	navigate(direction){
		if (!this.state.mdl || !this.state.mdl.isMulti || !this.state.now?.sim?.assCur)
			return this.noUpdate(6)

		const assets = this.state.now.sim.assCur
		let newIdx = this.state.mdl.curIdx

		if (direction == 'prev' && newIdx > 0) newIdx = newIdx - 1
		else if (direction == 'next' && newIdx < assets.length - 1) newIdx = newIdx + 1
		else return this.noUpdate(6)

		const curAss = assets[newIdx]
		const newMdl = {
			... this.state.mdl,
			curIdx: newIdx,
			imgUrl: `/api/img/${curAss.autoId}?q=preview`
		}

		const htms = this.buildImageContent(newMdl)
		const prevStyle = this.getPrevButtonStyle(newMdl)
		const nextStyle = this.getNextButtonStyle(newMdl)
		const selectText = this.getSelectButtonText(newMdl, curAss)
		const selectColor = this.getSelectButtonColor(newMdl, curAss)

		console.log(`[MdlImg] navigated to idx[${newIdx}] autoId[${curAss.autoId}]`)

		return [newMdl, htms, prevStyle, nextStyle, selectText, selectColor]
	},

	buildImageContent(mdl){
		const htms = []

		if (mdl.isMulti && this.state.now?.sim?.assCur && mdl.curIdx < this.state.now.sim.assCur.length) {
			const ass = this.state.now.sim.assCur[mdl.curIdx]

			if (ass && ass.vdoId) {
				htms.push(
					R.mk('div', {className: 'livephoto'},
						R.mk('video', {
							src: `/api/livephoto/${ass.autoId}`,
							id: `livephoto-modal-video-${ass.autoId}`,
							autoPlay: true,
							loop: true,
							muted: true,
							controls: false
						}),
						R.mk('div', {className: 'ctrls', id: 'livephoto-controls'},
							R.mk('button', {className: 'play-pause-btn', id: 'livephoto-play-pause'}, '⏸️'),
							R.mk('div', {className: 'progress-bar', id: 'livephoto-progress-bar'},
								R.mk('div', {className: 'progress-fill', id: 'livephoto-progress-fill'})
							),
							R.mk('div', {className: 'time-display', id: 'livephoto-time-display'}, '0:00 / 0:00')
						)
					)
				)
			}
			if (mdl.imgUrl) htms.push(R.mk('img', {src: mdl.imgUrl}))

			if (ass) {
				htms.push(
					R.mk('div', {className: 'acts B'},
						R.mk('span', {className: 'tag xl'}, `#${ass.autoId} @${ass.simGIDs?.join(',') || ''}`)
					)
				)
			}
		}
		else if (mdl.imgUrl) htms.push(R.mk('img', {src: mdl.imgUrl}))

		return htms
	},

	getPrevButtonStyle(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur || this.state.now.sim.assCur.length <= 1) return {display: 'none'}

		return {
			display: 'block',
			opacity: mdl.curIdx <= 0 ? '0.3' : '1'
		}
	},

	getNextButtonStyle(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur || this.state.now.sim.assCur.length <= 1) return {display: 'none'}

		return {
			display: 'block',
			opacity: mdl.curIdx >= this.state.now.sim.assCur.length - 1 ? '0.3' : '1'
		}
	},

	getSelectButtonText(mdl, curAss){
		if (!mdl.isMulti || !curAss) return '◻️ Select'

		const isSelected = this.state.ste?.selectedIds?.includes(curAss.autoId)
		return isSelected ? '✅ Selected' : '◻️ Select'
	},

	getSelectButtonColor(mdl, curAss){
		if (!mdl.isMulti || !curAss) return 'primary'

		const isSelected = this.state.ste?.selectedIds?.includes(curAss.autoId)
		return isSelected ? 'success' : 'primary'
	},

	noUpdate(cnt){return Array(cnt).fill(dash_clientside.no_update)},

	updMdl(){
		if (!this.state.mdl || !this.state.mdl.open) return this.noUpdate(12)

		const mdl = this.state.mdl
		let asset = this.getCurrentAsset()

		return [
			mdl.open,
			this.buildImageContent(mdl),
			this.getPrevButtonStyle(mdl),
			this.getNextButtonStyle(mdl),
			this.getSelectButtonStyle(mdl),
			this.getSelectButtonText(mdl, asset),
			this.getSelectButtonColor(mdl, asset),
			this.getHelpClassName(mdl),
			this.getHelpButtonText(mdl),
			this.getInfoClassName(mdl),
			this.getInfoButtonText(mdl),
			this.getInfoContent(mdl),
			this.getModeCss(mdl),
			this.getModeTxt(mdl),
		]
	},

	getCurrentAsset(){
		if (!this.state.mdl?.isMulti || !this.state.now?.sim?.assCur) return null

		const idx = this.state.mdl.curIdx
		const assets = this.state.now.sim.assCur
		return (idx >= 0 && idx < assets.length) ? assets[idx] : null
	},

	getSelectButtonStyle(mdl){return mdl.isMulti ? {display: 'block'} : {display: 'none'}},

	getInfoContent(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur) return []

		const ass = this.getCurrentAsset()
		if (!ass) return []

		const assetRows = [
			R.mk('tr', {},
				R.mk('td', {}, 'autoId'),
				R.mk('td', {},
					R.mk('span', {className: 'tag'}, `#${ass.autoId}`),
					R.mk('span', {className: 'tag'}, `@${ass.simGIDs?.join(',') || ''}`)
				)
			),
			R.mk('tr', {},
				R.mk('td', {}, 'id'),
				R.mk('td', {}, R.mk('span', {className: 'tag sm second'}, ass.id))
			),
			R.mk('tr', {},
				R.mk('td', {}, 'Filename'),
				R.mk('td', {}, ass.originalFileName)
			),
			R.mk('tr', {},
				R.mk('td', {}, 'Path'),
				R.mk('td', {}, ass.originalPath )
			)
		]

		const exifRows = this.buildExifRows(ass)
		const allRows = [... assetRows, ... exifRows]

		return R.mk('table', {className: 'table-sm table-striped', style: {width: '100%'}},
			R.mk('tbody', {}, ... allRows)
		)
	},

	buildExifRows(asset){
		const rows = []

		if (!asset.jsonExif) return rows

		const exifMap = {
			'exifImageWidth': 'Width',
			'exifImageHeight': 'Height',
			'fileSizeInByte': 'File Size',
			'dateTimeOriginal': 'Capture Time',
			'modifyDate': 'Modify Time',
			'make': 'Camera Brand',
			'model': 'Camera Model',
			'lensModel': 'Lens',
			'fNumber': 'Aperture',
			'focalLength': 'Focal Length',
			'exposureTime': 'Exposure Time',
			'iso': 'ISO',
			'orientation': 'Orientation',
			'latitude': 'Latitude',
			'longitude': 'Longitude',
			'city': 'City',
			'state': 'State',
			'country': 'Country',
			'description': 'Description',
			'fps': 'Frame Rate'
		}

		for ( const [key, displayKey] of Object.entries(exifMap) ){
			if (key in asset.jsonExif && asset.jsonExif[key] != null) {
				let value = asset.jsonExif[key]
				let displayValue = value

				if (key == 'fileSizeInByte') displayValue = this.formatFileSize(value)
				else if (key == 'focalLength' && typeof value == 'number') displayValue = `${value} mm`
				else if (key == 'fNumber' && typeof value == 'number') displayValue = `f/${value}`
				else if (value) displayValue = this.formatDate(value)

				if (displayValue) {
					rows.push(
						R.mk('tr', {},
							R.mk('td', {}, displayKey),
							R.mk('td', {}, displayValue)
						)
					)
				}
			}
		}

		return rows
	},

	formatFileSize(value){
		if (typeof value == 'number') {
			if (value > 1024 * 1024) {
				return `${(value / (1024 * 1024)).toFixed(2)} MB`
			}
			else if (value > 1024) {
				return `${(value / 1024).toFixed(2)} KB`
			}
			else {
				return `${value} B`
			}
		}
		return value
	},

	formatDate(value){
		const str = String(value)
		if (str.includes('T') && str.includes('+')) {
			const parts = str.split('T')
			if (parts.length == 2 && parts[1].includes('+')) {
				const timePart = parts[1]
				if (timePart.includes('.') && (timePart.includes('+') || timePart.includes('-'))) {
					const timeParts = timePart.split('.')
					if (timeParts.length == 2) {
						const baseTime = timeParts[0]
						const tzPart = timeParts[1].includes('+') ?
							timeParts[1].split('+')[1] : timeParts[1].split('-')[1]
						const sign = timeParts[1].includes('+') ? '+' : '-'
						const tz = `${baseTime}${sign}${tzPart}`
						return `${parts[0]} ${tz}`
					}
				}
			}
		}
		return str
	},


	getHelpClassName(mdl){
		if (!mdl.isMulti) return 'hide'
		return mdl.hideHelp ? 'help collapsed' : 'help'
	},
	getHelpButtonText(mdl){return mdl.hideHelp ? '❔' : '❎'},
	getInfoClassName(mdl){
		if (!mdl.isMulti) return 'hide'
		return mdl.hideInfo ? 'info collapsed' : 'info'
	},
	getInfoButtonText(mdl){return mdl.hideInfo ? 'ℹ️' : '❎'},
	getModeTxt(mdl){return mdl.modeH ?'Fit Screen' : 'Full Height'},
	getModeCss(mdl){return mdl.modeH ?'img-pop auto' : 'img-pop'},

	toggleHelp(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			hideHelp: !this.state.mdl.hideHelp
		}

		const helpCss = this.getHelpClassName(newMdl)
		const helpTxt = this.getHelpButtonText(newMdl)

		return [newMdl, helpCss, helpTxt]
	},

	toggleInfo(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			hideInfo: !this.state.mdl.hideInfo
		}

		const infoCss = this.getInfoClassName(newMdl)
		const infoTxt = this.getInfoButtonText(newMdl)

		return [newMdl, infoCss, infoTxt]
	},

	toggleMode(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			modeH: !this.state.mdl.modeH
		}

		let newCss = this.getModeCss(newMdl)
		let newTxt = this.getModeTxt(newMdl)

		return [newMdl, newCss, newTxt]
	}
}


//------------------------------------------------------------------------
// mdlImg
//------------------------------------------------------------------------
window.dash_clientside.mdlImg = {
	onStoreToDummy(mdl_data, now_data){
		if (mdl_data && mdl_data.isMulti && now_data && now_data.sim && now_data.sim.assCur) {
			let curIdx = mdl_data.curIdx
			let assets = now_data.sim.assCur

			if (curIdx >= 0 && curIdx < assets.length) {
				let curAsset = assets[curIdx]
				window.currentMdlImgAutoId = curAsset.autoId
				console.log('[mdlImg] Set current autoId for hotkeys:', window.currentMdlImgAutoId)
			}
		}
		else {
			window.currentMdlImgAutoId = null
		}
		return dash_clientside.no_update
	},
	onBtnSelectToSte(n_clicks){
		if (dash_clientside.callback_context.triggered.length > 0) {
			let triggered = dash_clientside.callback_context.triggered[0]
			if (triggered.prop_id && triggered.value > 0) {
				let mdl = arguments[arguments.length - 1] // mdlImg store data
				let now = arguments[arguments.length - 2] // now store data

				if (mdl && mdl.isMulti && now && now.sim && now.sim.assCur) {
					let curIdx = mdl.curIdx
					let assets = now.sim.assCur

					if (curIdx >= 0 && curIdx < assets.length) {
						let curAsset = assets[curIdx]
						let autoId = curAsset.autoId

						if (Ste) {
							Ste.toggle(autoId)

							let selectedIds = Array.from(Ste.selectedIds)
							let ste = {
								selectedIds,
								cntTotal: Ste.cntTotal
							}
							console.log('[mdlImg] Toggled autoId:', autoId, 'ste:', ste)
							return ste
						}
					}
				}
			}
		}
		return dash_clientside.no_update
	},

	onNavigation(prevClk, nextClk, now, ste, mdl){
		const ctx = dash_clientside.callback_context
		if (!ctx.triggered.length) return dash_clientside.no_update

		MdlImg.init(mdl, now, ste)

		const trigId = ctx.triggered[0].prop_id
		if (trigId.includes('btn-img-prev')) return MdlImg.navigate('prev')
		if (trigId.includes('btn-img-next')) return MdlImg.navigate('next')

		return dash_clientside.no_update
	},

	onUpdMdl(mdl, now, ste){
		MdlImg.init(mdl, now, ste)
		return MdlImg.updMdl()
	},

	onHelpToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		MdlImg.init(mdl, null, null)
		return MdlImg.toggleHelp()
	},

	onInfoToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		MdlImg.init(mdl, null, null)
		return MdlImg.toggleInfo()
	},

	onModeToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		return MdlImg.toggleMode()
	},

	onSteChanged(ste, now, mdl){
		if (!ste || !now || !mdl) return Array(2).fill(dash_clientside.no_update)

		MdlImg.init(mdl, now, ste)

		if (!mdl.isMulti || !now.sim?.assCur || mdl.curIdx >= now.sim.assCur.length) return Array(2).fill(dash_clientside.no_update)

		const curAss = now.sim.assCur[mdl.curIdx]
		if (!curAss) return Array(2).fill(dash_clientside.no_update)

		const selectText = MdlImg.getSelectButtonText(mdl, curAss)
		const selectColor = MdlImg.getSelectButtonColor(mdl, curAss)

		console.log(`[MdlImg] Updated button state for autoId[${curAss.autoId}]`)

		return [selectText, selectColor]
	}
}


document.addEventListener('keydown', function(ev){
	const div = document.querySelector('#img-modal')

	if (!div || !div.parentElement.classList.contains('show')) return
	if (ev.key == 'ArrowLeft' || ev.key == 'h') {
		ev.preventDefault()
		const btn = document.querySelector('#btn-img-prev')
		if (btn && btn.style.opacity != '0.3') btn.click()
	}
	else if (ev.key == 'ArrowRight' || ev.key == 'l') {
		ev.preventDefault()
		const btn = document.querySelector('#btn-img-next')
		if (btn && btn.style.opacity != '0.3') btn.click()
	}
	else if (ev.key == ' ') {
		ev.preventDefault()

		if (Ste && window.currentMdlImgAutoId) {
			Ste.toggle(window.currentMdlImgAutoId)

			const { cntTotal, selectedIds } = Ste

			console.log('[mdlImg Hotkey] Space toggled autoId:', window.currentMdlImgAutoId)

			dsh.syncSte(cntTotal, selectedIds)
		}
	}
	else if (ev.key == 'Escape' || ev.key == 'q') {
		ev.preventDefault()
		const btn = div.querySelector('.btn-close')
		if (btn) btn.click()
	}
	else if (ev.key == 'm') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-mode')
		if (btn) btn.click()
	}
	else if (ev.key == 'i') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-info')
		if (btn) btn.click()
	}

	else if (ev.key == '?') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-help')
		if (btn) btn.click()
	}
})

