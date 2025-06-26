
//------------------------------------------------------------------------
// WS
//------------------------------------------------------------------------
const k = {
	wsId: 'global-ws',
}

const TskWS = {
	socket: null,
	wsConfig: null,
	isConnecting: false,
	isConnected: false,
	timeout: 2000,
	fnTimeout: null,
	fnConned: null,
	fnErroed: null,

	init( fnConned, fnErroed )
	{
		this.fnConned = fnConned
		this.fnErroed = fnErroed
		dsh.syncStore( k.wsId, {} ) //init all null, let backend know conection status

		if (typeof io === 'undefined') {
			console.error('[wst] WebSocket client library not found');
			notify('❌ WebSocket client library not found. Task functionality unavailable.', 'error');
			return;
		}

		window.addEventListener( 'beforeunload', () => this.disconnect() )
		this.connect()
	},
	connect()
	{
		if ( this.isConnecting || this.isConnected ) return

		this.isConnecting = true

		console.log( `[wst] Connecting to server...` )

		this.fnTimeout = setTimeout( () => {
			if ( this.socket && !this.isConnected )
			{
				console.warn( '[wst] Connection timeout' )
				this.socket.disconnect()
				this.onError( 'Connection timeout' )
			}
		}, 5000 )

		try
		{
			let wsUrl = '/'
			if (this.wsConfig && this.wsConfig.isDevUI) {
				const currentPort = parseInt(window.location.port) || 8086
				const wsPort = currentPort + 1
				wsUrl = `:${wsPort}`
			}
			console.log(`[wst] Connecting...`)

			this.socket = io(wsUrl, { transports: ['websocket', 'polling'], upgrade: true, reconnection: true })

			this.socket.on('connect', this.onConn.bind(this));
			this.socket.on('task_message', this.onMsg.bind(this));
			this.socket.on('disconnect', this.onClose.bind(this));
			this.socket.on('connect_error', this.onError.bind(this));
		}
		catch ( error )
		{
			console.error( '[wst] WebSocket creation failed:', error )
			this.onError( error.message )
		}
	},

	schedule()
	{
		setTimeout( () => {
			console.info(`[wst] reconnecting..`)
			this.connect()
		}, 5000 )
	},

	clearCnnTimeout()
	{
		if ( this.fnTimeout )
		{
			clearTimeout( this.fnTimeout )
			this.fnTimeout = null
		}
	},

	onConn()
	{
		this.clearCnnTimeout()
		this.isConnecting = false
		this.isConnected = true

		this.fnConned()
	},

	onError( error )
	{
		console.error( '[wst] Error:', error )
		this.clearCnnTimeout()
		this.isConnecting = false
		this.isConnected = false

		this.updStoreWs( { err: typeof error === 'string' ? error : 'Connection error' } )
		//notify('❌ WebSocket connection failed. Task functionality is unavailable.', 'error')
		this.fnErroed()
		this.schedule()
	},

	onClose( reason )
	{
		console.log( `[wst] Connection closed: ${ reason }` )
		this.clearCnnTimeout()
		this.isConnecting = false
		this.isConnected = false

		this.updStoreWs( { err: reason || 'Connection closed' } )

		this.schedule()
	},

	onMsg( data )
	{
		try
		{
			if ( !data || typeof data !== 'object' )
			{
				console.error( `[wst] invalid message format:`, data )
				return
			}

			this.updStoreWs( data )

		}
		catch ( error )
		{
			console.error( '[wst] Message processing error:', error )
		}
	},

	updStoreWs( state )
	{
		dsh.syncStore( k.wsId, state )

		// const event = new CustomEvent('ws-status-change', {
		//     detail: { state, error }
		// })
		// document.dispatchEvent(event)
	},

	send( message )
	{
		if ( this.isConnected && this.socket && this.socket.connected )
		{
			this.socket.emit('message', message)
			return true
		}
		else
		{
			console.warn( '[wst] Cannot send message - not connected' )
			return false
		}
	},

	disconnect()
	{
		this.clearCnnTimeout()
		if ( this.socket ) this.socket.disconnect()
	}
}
