// Owns which sections of the page are visible, using only the `hidden` attribute.
// One screen shows at a time: setup, Lobby, playing or game over.

const SECTIONS = [
  'controls-new-or-join',
  'joinGameConfigBox',
  'controls-waiting-for-start',
  'controls-start',
  'lobby-qr',
  'game',
  'timelineHeader',
  'songCount',
  'songTimeline',
  'newSongContainer',
  'winnerHeader'
]

const TIMELINE = ['game', 'timelineHeader', 'songCount', 'songTimeline']

let current = null
let lobbyQrLoaded = false

const visibleSections = (screen, { hostAndJoin, sessionChoice, isHost, newSong }) => {
  switch (screen) {
    case 'setup':
      return [
        hostAndJoin && 'controls-new-or-join',
        sessionChoice && 'joinGameConfigBox'
      ]
    case 'lobby':
      return [
        'controls-waiting-for-start',
        isHost && 'controls-start',
        lobbyQrLoaded && 'lobby-qr'
      ]
    case 'playing':
      return [...TIMELINE, newSong && 'newSongContainer']
    case 'gameOver':
      return [...TIMELINE, 'winnerHeader']
    default:
      throw new Error(`Unknown screen: ${screen}`)
  }
}

// Options: `hostAndJoin` and `sessionChoice` for setup, `isHost` for the Lobby,
// `newSong` for playing.
export function showScreen (
  screen,
  { hostAndJoin = true, sessionChoice = false, isHost = false, newSong = false } = {}
) {
  current = { screen, options: { hostAndJoin, sessionChoice, isHost, newSong } }
  const visible = new Set(visibleSections(screen, current.options).filter(Boolean))
  for (const id of SECTIONS) {
    document.getElementById(id).hidden = !visible.has(id)
  }
}

export const currentScreen = () => current?.screen ?? null

const refresh = () => {
  if (current) {
    showScreen(current.screen, current.options)
  }
}

// The Lobby QR code shows in the Lobby once its image has loaded.
export function loadLobbyQr (src) {
  const img = document.getElementById('lobbyQrImg')
  lobbyQrLoaded = false
  img.onerror = () => {
    lobbyQrLoaded = false
    refresh()
  }
  img.onload = () => {
    lobbyQrLoaded = true
    refresh()
  }
  img.src = src
}

function toggleLobbyQrSize () {
  const img = document.getElementById('lobbyQrImg')
  const bigger = img.classList.toggle('bigger')
  const button = document.getElementById('lobbyQrToggleBtn')
  button.textContent = bigger ? 'Show smaller' : 'Show bigger'
  button.setAttribute('aria-pressed', String(bigger))
}

document.getElementById('lobbyQrToggleBtn').onclick = () => toggleLobbyQrSize()
