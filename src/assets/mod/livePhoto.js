
//------------------------------------------------------------------------
// LivePhoto Management
//------------------------------------------------------------------------
const key = 'livephoto'
const keyc = `.${key}`
const LivePhoto = window.LivePhoto = {
	hoveredVideo: null,
	modalVideo: null,

	init()
	{
		this.setupVideoErrorHandling()
		this.setupModalControls()
	},

	setupVideoErrorHandling()
	{
		const handleVdoList = (video) => {

			if (video.dataset.livephotoHandled) return
			video.dataset.livephotoHandled = 'true'
			video.addEventListener('error', () => {
				console.warn('[LivePhoto] load failed, hidden:', video.src)

				video.style.display = 'none'
				const span = video.closest('.viewer').querySelector(`span.livePhoto`)
				if(!span) {
					console.warn(`not found ${keyc} in viewer`)
					return
				}
				if(span) {
					span.innerText = `LivePhoto (can't play)`
					span.classList.add('red')
				}
				else {
					span.innerText = `LivePhoto`
					span.classList.remove('red')
				}
			})

			video.addEventListener('loadstart', () => {
				video.addEventListener('canplay', () => {
				}, { once: true })
			})
		}

		const handleModalVideo = (video) => {
			if (video.dataset.modalHandled) return
			video.dataset.modalHandled = 'true'

			const modal = video.closest('#img-modal')
			if (!modal) return

			const img = modal.querySelector('img')
			if (!img) return

			video.style.display = 'none'
			img.style.display = 'none'

			video.addEventListener('canplay', () => {
				video.style.display = 'block'
				img.style.display = 'none'
			}, { once: true })

			video.addEventListener('error', () => {
				video.style.display = 'none'
				img.style.display = 'block'
			}, { once: true })
		}

		document.querySelectorAll(keyc).forEach(handleVdoList)
		document.querySelectorAll('#img-modal .livephoto video').forEach(handleModalVideo)

		const observer = new MutationObserver((mus) => {
			mus.forEach(mu => {
				mu.addedNodes.forEach(node => {
					if (node.nodeType == 1) {
						if (node.classList?.contains(key)) handleVdoList(node)
						if (node.querySelectorAll) {
							node.querySelectorAll(keyc).forEach(handleVdoList)
							node.querySelectorAll('#img-modal .livephoto video').forEach(handleModalVideo)
						}
					}
				})
			})
		})

		observer.observe(document.body, { childList: true, subtree: true })
	},

	setupModalControls()
	{
		document.addEventListener( 'click', ( e ) => {
			if ( e.target.id == 'livephoto-play-pause' )
			{
				this.toggleModalPlayback()
			}
			else if ( e.target.id == 'livephoto-progress-bar' || e.target.parentElement?.id == 'livephoto-progress-bar' )
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
