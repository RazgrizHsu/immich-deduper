const Nfy = {
	storeKey: 'store-nfy',
	_pendingMsgs: [],

	_getTimeId() {
		return Date.now().toString(36) + Math.random().toString(36).substr(2, 5)
	},


	_addToStore(msg, typ, timeout = 5000) {
		const msgData = {
			id: this._getTimeId(),
			message: msg,
			type: typ,
			timeout: timeout
		}

		this._pendingMsgs.push(msgData)

		setTimeout(() => {
			if (this._pendingMsgs.length > 0) {
				const msgsToAdd = [...this._pendingMsgs]
				this._pendingMsgs = []
				dsh.syncStore('hidden-add-trigger', msgsToAdd)
			}
		}, 0)

		console.info(`[Nfy] Queued (${typ}) "${msg}", id: ${msgData.id}`)
		return msgData
	},

	info(msg, timeout = 5000) {
		this._addToStore(msg, 'info', timeout)
	},

	success(msg, timeout = 5000) {
		this._addToStore(msg, 'success', timeout)
	},

	warn(msg, timeout = 8000) {
		this._addToStore(msg, 'warning', timeout)
	},

	error(msg, timeout = 0) {
		this._addToStore(msg, 'danger', timeout)
	}
}

window.dash_clientside.notify = {
	add(msgsToAdd, nfyData) {

		if (!msgsToAdd || !Array.isArray(msgsToAdd) || msgsToAdd.length === 0) return dsh.noUpd

		const currentData = nfyData || { msgs: [] }
		if (!currentData.msgs) currentData.msgs = []

		currentData.msgs.push(...msgsToAdd)

		// console.info(`[nfy:add] len(${msgsToAdd.length}), total: ${currentData.msgs.length}`)
		return currentData
	},


	autoRemove(msgId, nfyData) {
		// console.info(`[nfy:arm] msgId: ${msgId}`)

		if (!msgId || !nfyData || !nfyData.msgs) {
			console.error(`[nfy:arm] invalid params`)
			return dsh.noUpd
		}

		const newMsgs = nfyData.msgs.filter(msg => msg.id !== msgId)
		const newData = { ...nfyData, msgs: newMsgs }
		// console.info(`[nfy:arm] id[${msgId}] rst: ${newMsgs.length}`)

		return newData
	},
}

document.addEventListener('DOMContentLoaded', () => {

	const processedNotifications = new Set()

	const setAuRm = () => {
		const container = document.getElementById('div-notify')
		if (!container) {
			console.log('[aurm] no container found')
			return
		}

		const boxes = container.querySelectorAll('.box')
		// console.log(`[aurm] found ${boxes.length} boxes`)

		boxes.forEach(box => {
			const timeout = parseInt(box.dataset.msgTimeout)
			const msgId = box.dataset.msgId
			const isProcessed = processedNotifications.has(msgId)

			// console.log(`[aurm] box: msgId=${msgId}, timeout=${timeout}, isProcessed=${isProcessed}`)

			if (timeout && timeout > 0 && !isProcessed) {
				processedNotifications.add(msgId)
				// console.log(`[aurm] setting timeout for msgId=${msgId}, timeout=${timeout}ms`)
				setTimeout(() => {
					dsh.syncStore('hidden-auto-remove-trigger', msgId)
					processedNotifications.delete(msgId)
				}, timeout)
			}
		})
	}

	ui.mob.waitFor('#div-notify', (container) => {
		console.log('[aurm] container found, setting up auto-remove')

		setAuRm()

		const observer = new MutationObserver(() => {
			console.log('[aurm] DOM changed, running setAuRm')
			setAuRm()
		})

		observer.observe(container, {
			childList: true
		})
		console.log('[aurm] observer started')
	}, '[nfy]')
})
