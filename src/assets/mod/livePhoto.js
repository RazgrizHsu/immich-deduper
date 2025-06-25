
//------------------------------------------------------------------------
// LivePhoto Management
//------------------------------------------------------------------------
const LivePhoto = window.LivePhoto = {
	hoveredVideo: null,
	modalVideo: null,

	init()
	{
		this.setupHover()
		this.setupModalControls()
	},

	setupHover()
	{
		document.addEventListener( 'mouseenter', ( e ) => {
			const card = e.target.closest( '.card' )
			if ( !card ) return

			const livePhotoOverlay = card.querySelector( '.livephoto-overlay' )
			if ( !livePhotoOverlay || livePhotoOverlay.style.display == 'none' ) return

			const video = livePhotoOverlay.querySelector( '.livephoto-video' )
			if ( video )
			{
				this.hoveredVideo = video
				video.style.display = 'block'
				video.play().catch( e => console.warn( 'Video play failed:', e ) )
			}
		}, true )

		document.addEventListener( 'mouseleave', ( e ) => {
			const card = e.target.closest( '.card' )
			if ( !card ) return

			if ( this.hoveredVideo )
			{
				this.hoveredVideo.pause()
				this.hoveredVideo.currentTime = 0
				this.hoveredVideo.style.display = 'none'
				this.hoveredVideo = null
			}
		}, true )
	},

	setupModalControls()
	{
		document.addEventListener( 'click', ( e ) => {
			if ( e.target.id == 'livephoto-play-pause' )
			{
				this.toggleModalPlayback()
			}
			else if ( e.target.id == 'livephoto-progress-bar' || e.target.parentElement.id == 'livephoto-progress-bar' )
			{
				this.seekModalVideo( e )
			}
		} )

		setInterval( () => { this.updateModalProgress() }, 100 )
	},

	toggleModalPlayback()
	{
		const video = document.querySelector( '.livephoto video' )
		const button = document.getElementById( 'livephoto-play-pause' )

		if ( !video || !button ) return

		if ( video.paused )
		{
			video.play()
			button.textContent = '⏸️'
		}
		else
		{
			video.pause()
			button.textContent = '▶️'
		}
	},

	seekModalVideo( e )
	{
		const video = document.querySelector( '.livephoto video' )
		const progressBar = document.getElementById( 'livephoto-progress-bar' )

		if ( !video || !progressBar ) return

		const rect = progressBar.getBoundingClientRect()
		const clickX = e.clientX - rect.left
		const percentage = clickX / rect.width
		const seekTime = percentage * video.duration

		video.currentTime = seekTime
	},

	updateModalProgress()
	{
		const video = document.querySelector( '.livephoto video' )
		const progressFill = document.getElementById( 'livephoto-progress-fill' )
		const timeDisplay = document.getElementById( 'livephoto-time-display' )

		if ( !video || !progressFill || !timeDisplay ) return

		if ( video.duration > 0 )
		{
			const percentage = ( video.currentTime / video.duration ) * 100
			progressFill.style.width = percentage + '%'

			const currentMin = Math.floor( video.currentTime / 60 )
			const currentSec = Math.floor( video.currentTime % 60 )
			const totalMin = Math.floor( video.duration / 60 )
			const totalSec = Math.floor( video.duration % 60 )

			timeDisplay.textContent = `${ currentMin }:${ currentSec.toString().padStart( 2, '0' ) } / ${ totalMin }:${ totalSec.toString().padStart( 2, '0' ) }`
		}
	}
}

if ( document.readyState == 'loading' )
{
	document.addEventListener( 'DOMContentLoaded', () => LivePhoto.init() )
}
else
{
	LivePhoto.init()
}
