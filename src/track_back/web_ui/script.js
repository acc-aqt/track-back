'use strict'

let socket
let sessionName
let username
let isHost = false

let serverUrl = ''

let pingInterval = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10

const NAME_PATTERN = /^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u
const USERNAME_MAX_LENGTH = 20
const SESSION_NAME_MAX_LENGTH = 40
const FALLBACK_COVER = 'dummy-cover/cover1.webp'

function loadScript (url, onSuccess, onError) {
  const script = document.createElement('script')
  script.src = url
  script.onload = onSuccess
  script.onerror = onError
  document.head.appendChild(script)
}

// Get serverurl by user input if server_config.js does not exist.
loadScript(
  'server_config.js',
  () => {
    console.log('✅ Loaded server_config.js')
    serverUrl = window.TRACK_BACK_CONFIG?.TRACK_BACK_SERVER_URL || ''
    document.getElementById('controls-server').hidden = true
    startApp()
  },
  () => {
    console.info('No server_config.js found, asking for the server URL.')
    document.getElementById('controls-server').hidden = false
    const input = document.getElementById('server')
    serverUrl = input?.value?.trim()?.replace(/\/+$/, '') || ''
    startApp()
  }
)

function getServerUrl () {
  if (window.TRACK_BACK_CONFIG?.TRACK_BACK_SERVER_URL) {
    return window.TRACK_BACK_CONFIG.TRACK_BACK_SERVER_URL
  }

  // fallback: dynamic value from input field
  const input = document.getElementById('server')
  return input?.value?.trim()?.replace(/\/+$/, '') || ''
}

function startApp () {
  console.log('🌐 Using server URL:', serverUrl)
  prefillStoredUsername()
  handleJoinLink()
}

const USERNAME_STORAGE_KEY = 'trackback.username'

const loadStored = key => {
  try {
    return localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

const store = (key, value) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Storage can be unavailable (private mode); the value is then just not remembered.
  }
}

const loadStoredUsername = () => loadStored(USERNAME_STORAGE_KEY)

const storeUsername = name => store(USERNAME_STORAGE_KEY, name)

function prefillStoredUsername () {
  const input = document.getElementById('username')
  if (!input.value) {
    input.value = loadStoredUsername()
  }
}

// Join link: /?join=<Game Session Name>[&username=<Username>][&host=1]
// Used by the Spotify callback redirect (with host=1) and the Lobby QR code.
function readJoinLink () {
  const url = new URL(window.location.href)
  const session = url.searchParams.get('join')
  const linkUsername = url.searchParams.get('username')
  const host = url.searchParams.get('host') === '1'
  if (session === null && linkUsername === null && !host) {
    return null
  }
  url.searchParams.delete('join')
  url.searchParams.delete('username')
  url.searchParams.delete('host')
  window.history.replaceState(window.history.state, '', url)
  return session ? { session, username: linkUsername, host } : null
}

async function handleJoinLink () {
  const link = readJoinLink()
  if (!link) {
    return
  }
  isHost = link.host
  const input = document.getElementById('username')
  if (link.username) {
    input.value = link.username.trim()
  }
  if (isValidUsername(input.value.trim())) {
    await joinSession(link.session)
  } else {
    askUsernameThenJoin(link.session)
  }
}

function askUsernameThenJoin (session) {
  showSessionChoice([session])
  document.getElementById('joinGameTitle').textContent =
    'Enter your username to join'
  document.getElementById('username').focus()
}

// Music Service choice in Game Setup: "Music: <service> · change".
const MUSIC_SERVICE_LABELS = {
  spotify: 'Spotify 📻🎶',
  applemusic: 'Apple Music 🍎🎶',
  mock: 'Mock Music Service'
}

// Older servers have no /music-services; offer the real services as before.
const OLDER_SERVER_MUSIC_SERVICES = {
  default: 'spotify',
  available: ['spotify', 'applemusic'],
  fromOlderServer: true
}

async function fetchMusicServices () {
  try {
    const res = await fetch(`${serverUrl}/music-services`)
    if (res.status === 404) {
      return OLDER_SERVER_MUSIC_SERVICES
    }
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    return await res.json()
  } catch (err) {
    console.error('❌ Failed to fetch music services:', err)
    return OLDER_SERVER_MUSIC_SERVICES
  }
}

// Fill the Music line for the given services; `preferred` wins if still available.
function showMusicServiceChoice (services, preferred = null) {
  const dropdown = document.getElementById('musicServiceDropdown')
  dropdown.replaceChildren(
    ...services.available.map(service => {
      const option = document.createElement('option')
      option.value = service
      option.textContent = MUSIC_SERVICE_LABELS[service] || service
      return option
    })
  )
  dropdown.value = services.available.includes(preferred)
    ? preferred
    : services.default

  const showDropdown = Boolean(services.fromOlderServer)
  document.getElementById('musicServiceName').textContent =
    MUSIC_SERVICE_LABELS[dropdown.value] || dropdown.value
  document.getElementById('musicServiceChange').hidden =
    services.available.length < 2
  document.getElementById('musicServiceLine').hidden = showDropdown
  document.getElementById('musicServicePicker').hidden = !showDropdown
}

async function loadMusicServiceChoice (preferred = null) {
  const services = await fetchMusicServices()
  showMusicServiceChoice(services, preferred)
  return services
}

function selectedMusicService () {
  return document.getElementById('musicServiceDropdown').value
}

document.getElementById('musicServiceChangeBtn').onclick = () => {
  document.getElementById('musicServiceLine').hidden = true
  document.getElementById('musicServicePicker').hidden = false
  document.getElementById('musicServiceDropdown').focus()
}

let currentGuessSong = null
let pauseAfterGuess = false
let queuedGuessRequest = null

const WRONG_GUESS_DISPLAY_TIME = 2000
const FADE_DURATION = 1000

const log = msg => {
  const logBox = document.getElementById('log')
  logBox.textContent += msg + '\n'
  logBox.scrollTop = logBox.scrollHeight
}

const targetSongCountInput = document.getElementById('targetSongCountInput')

targetSongCountInput.addEventListener('input', () => {
  let value = targetSongCountInput.value.trim()

  if (!/^\d+$/.test(value) || parseInt(value) <= 0) {
    targetSongCountInput.value = ''
  }
})

const isValidUsername = name =>
  name.length <= USERNAME_MAX_LENGTH && NAME_PATTERN.test(name)

const isValidSessionName = id =>
  id.length <= SESSION_NAME_MAX_LENGTH && NAME_PATTERN.test(id)

const readUsername = () => {
  const name = document.getElementById('username').value.trim()
  if (!name) {
    alert('Please enter a username!')
    return null
  }
  if (!isValidUsername(name)) {
    alert(
      `Usernames can have up to ${USERNAME_MAX_LENGTH} letters, digits, "_", "-" and single spaces.`
    )
    return null
  }
  return name
}

const describeHttpError = data => {
  const detail = data?.detail
  if (Array.isArray(detail)) {
    return detail.map(d => d.msg).join('; ')
  }
  return detail || 'Unknown error'
}

const handleHttpError = (data, prefix = '❌ Server error') => {
  log(`${prefix}: ${describeHttpError(data)}`)
}

// The server sends either a full URL (Spotify) or a path on itself (Apple Music).
const coverSrc = song => {
  const url = song.album_cover_url
  if (!url) return FALLBACK_COVER
  return url.startsWith('/') ? `${serverUrl}${url}` : url
}

const buildSongEntry = (song, extraClass = '') => {
  const entry = document.createElement('div')
  entry.className = extraClass ? `song-entry ${extraClass}` : 'song-entry'

  const cover = document.createElement('img')
  cover.className = 'song-cover'
  cover.alt = 'cover'
  cover.onerror = () => {
    cover.onerror = null
    cover.src = FALLBACK_COVER
  }
  cover.src = coverSrc(song)

  const details = document.createElement('div')
  details.className = 'song-details'
  const title = document.createElement('strong')
  title.textContent = song.title
  details.append(
    title,
    ` (${song.release_year})`,
    document.createElement('br'),
    `by ${song.artist}`
  )

  entry.append(cover, details)
  return entry
}

function handleGuessRequest (data) {
  if (pauseAfterGuess) {
    queuedGuessRequest = data
    return
  }
  const isForMe = data.next_player === username
  if (!isForMe) {
    return
  }

  showTimeline(data.song_list || [])

  const dummyCovers = [
    'dummy-cover/cover1.webp',
    'dummy-cover/cover2.webp',
    'dummy-cover/cover3.webp',
    'dummy-cover/cover4.webp',
    'dummy-cover/cover5.webp',
    'dummy-cover/cover6.webp'
  ]
  const randomCover =
    dummyCovers[Math.floor(Math.random() * dummyCovers.length)]

  document.getElementById('newSongContainer').innerHTML = `
    <div class="song-entry highlight" id="new-song">
      <img src="${randomCover}" alt="cover" class="song-cover" />
      <div class="song-details">
        <strong>Drag the song to the right place in the timeline.</strong>
      </div>
    </div>
  `

  document.getElementById('newSongContainer').style.display = 'block'

  setupDragDrop()
}

function showLobbyQr () {
  const img = document.getElementById('lobbyQrImg')
  img.onerror = hideLobbyQr
  img.onload = () => {
    document.getElementById('lobby-qr').hidden = false
  }
  img.src = `${serverUrl}/join-qr.svg?session=${encodeURIComponent(sessionName)}`
}

function hideLobbyQr () {
  const img = document.getElementById('lobbyQrImg')
  img.onload = null
  document.getElementById('lobby-qr').hidden = true
}

function toggleLobbyQrSize () {
  const img = document.getElementById('lobbyQrImg')
  const bigger = img.classList.toggle('bigger')
  const button = document.getElementById('lobbyQrToggleBtn')
  button.textContent = bigger ? 'Show smaller' : 'Show bigger'
  button.setAttribute('aria-pressed', String(bigger))
}

function showTimeline (list) {
  hideLobbyQr()
  document.getElementById('timelineHeader').style.display = 'block'
  document.getElementById('songTimeline').style.display = 'block'
  document.getElementById('songCount').style.display = 'block'
  document.getElementById('controls-waiting-for-start').hidden = true
  document.getElementById('controls-start').hidden = true

  document.getElementById('songCount').textContent = `Song count: ${list.length}`
  document
    .getElementById('songTimeline')
    .replaceChildren(...list.map(s => buildSongEntry(s)))
}

function handleGuessResult (data) {
  if (data.result === 'correct') {
    log(`✅ Guess was correct: ${data.message}`)
    document.getElementById(
      'songCount'
    ).textContent = `Song count: ${data.song_list.length}`
  } else {
    log(`❌ Guess was wrong: ${data.message}`)
  }

  const list = data.song_list || []

  const timeline = document.getElementById('songTimeline')

  document.getElementById('newSongContainer').style.display = 'none'

  // Update the timeline first (without the guess)
  timeline.replaceChildren(...list.map(s => buildSongEntry(s)))

  if (data.result === 'wrong') {
    const wrongSong = data.last_song || {}
    const guessedIndex = Number(data.last_index ?? 0)

    const wrongSongEl = buildSongEntry(wrongSong, 'wrong-guess')
    const wrongLabel = document.createElement('span')
    wrongLabel.className = 'wrong-label'
    wrongSongEl.prepend(wrongLabel)

    const children = timeline.children

    if (guessedIndex >= 0 && guessedIndex < children.length) {
      timeline.insertBefore(wrongSongEl, children[guessedIndex])
    } else {
      timeline.appendChild(wrongSongEl)
    }

    setTimeout(() => {
      wrongSongEl.classList.add('fade-out')
      setTimeout(() => {
        wrongSongEl.remove()
      }, FADE_DURATION)
    }, WRONG_GUESS_DISPLAY_TIME)

    pauseAfterGuess = true
    setTimeout(() => {
      pauseAfterGuess = false

      // If a guess request came in while we were paused, now we handle it
      if (queuedGuessRequest) {
        handleGuessRequest(queuedGuessRequest)
        queuedGuessRequest = null
      }
    }, WRONG_GUESS_DISPLAY_TIME + FADE_DURATION)
  }
}

const handleGameOver = data => {
  log(`🏁 Game Over! Winner: ${data.winner}`)
  document.getElementById('newSongContainer').style.display = 'none'
  const winnerHeader = document.getElementById('winnerHeader')
  const winnerIsYou = data.winner === username
  winnerHeader.replaceChildren(
    ...(winnerIsYou
      ? ['🎉 You win! 🎉', document.createElement('br'), '👩🏻‍🎤 🏆']
      : [
          'Game over.',
          document.createElement('br'),
          `${data.winner} won the game.`
        ])
  )

  winnerHeader.style.display = 'block'
}

const serverMessageHandlers = {
  your_turn: handleGuessRequest,
  guess_result: data => {
    if (data.player === username) {
      handleGuessResult(data)
    }
  },
  welcome: data => log(`👋🏻 ${data.message}`),
  player_joined: data => log(`👋🏻 ${data.message}`),
  player_rejoined: data => {
    if (data.user_name === username) {
      document.getElementById('newSongContainer').style.display = 'none'
      showTimeline(data.song_list || [])
      log('👋🏻 Welcome back! Waiting for the others to guess.')
    } else {
      log(`👋🏻 ${data.message}`)
    }
  },
  error: data => log(`🚨 Error: ${data.message}`),
  other_player_guess: data => log(`🧑🏽‍🎤 ${data.message}`),
  game_over: handleGameOver,
  user_disconnected: data => log(`❌ ${data.message}`)
}

function connectWebSocket () {
  const urlObj = new URL(serverUrl)
  const wsProtocol = urlObj.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${urlObj.host}/ws/${encodeURIComponent(
    sessionName
  )}/${encodeURIComponent(username)}`

  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    document.getElementById('game').style.display = 'block'
    log('🔌 Connected to game session.')

    reconnectAttempts = 0

    // Start keepalive ping
    pingInterval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }))
      }
    }, 10000)
  }
  socket.onerror = e => {
    console.error('🚨 WebSocket error:', e)
    log('🚨 WebSocket encountered an error.')
  }

  socket.onmessage = event => {
    try {
      const data = JSON.parse(event.data)
      if (Object.hasOwn(serverMessageHandlers, data.type)) {
        serverMessageHandlers[data.type](data)
      } else {
        log(`Unknown message type: ${data.type}.`)
      }
    } catch (e) {
      console.error('❌ Error parsing WebSocket message:', e)
      log('❌ Received invalid data from server.')
    }
  }

  socket.onclose = () => {
    log('❌ Connection closed. Attempting to reconnect...')

    clearInterval(pingInterval)

    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++
      setTimeout(() => {
        log(`🔁 Reconnecting attempt ${reconnectAttempts}...`)
        connectWebSocket()
      }, 2000 * reconnectAttempts) // Linear backoff
    } else {
      log('❌ Max reconnect attempts reached. Please reload the page.')
    }
  }
}

window.addEventListener('online', () => {
  if (!socket || socket.readyState === WebSocket.CLOSED) {
    log('🌐 Network back online. Reconnecting WebSocket...')
    connectWebSocket()
  }
})
async function fetchJoinableSessions () {
  try {
    const res = await fetch(`${serverUrl}/list-sessions`)
    const data = await res.json()
    if (!res.ok) {
      handleHttpError(data)
      return null
    }
    return data.sessions || []
  } catch (err) {
    console.error('❌ Failed to fetch sessions:', err)
    alert('⚠️ Failed to fetch game sessions.')
    return null
  }
}

function showSessionChoice (sessions) {
  document.getElementById('joinGameConfigBox').hidden = false
  document.getElementById('joinGameTitle').textContent = 'Select game to join'

  const dropdown = document.getElementById('sessionDropdown')
  dropdown.replaceChildren(
    ...sessions.map((name, index) => {
      const option = document.createElement('option')
      option.value = name
      option.textContent = `${index + 1}. ${name}`
      return option
    })
  )

  document.getElementById('joinSelectedSessionBtn').onclick = async () => {
    if (!dropdown.value) {
      alert('❌ Please select a session.')
      return
    }
    await joinSession(dropdown.value)
  }
}

async function joinSession (name) {
  sessionName = name
  const success = await joinGame()
  if (success) {
    document.getElementById('controls-new-or-join').hidden = true
    document.getElementById('controls-waiting-for-start').hidden = false
  }
  return success
}

async function joinGame () {
  try {
    username = readUsername()
    if (!username) {
      return false
    }
    const res = await fetch(`${serverUrl}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: sessionName, user_name: username })
    })

    const data = await res.json()

    if (!res.ok) {
      handleHttpError(data, '❌ Failed to join game')
      return false
    }

    log(`✅ Joined game: ${sessionName}`)
    storeUsername(username)
    connectWebSocket()
    showLobbyQr()
    if (isHost) {
      document.getElementById('controls-start').hidden = false
    }
    document.getElementById('joinGameConfigBox').hidden = true
    return true
  } catch (err) {
    console.error('❌ Failed to join game:', err)
    return false
  }
}

// Hosting: "Host a game" creates the Game Session right away with these
// defaults; "Options" reveals them for editing first.
const TARGET_SONG_COUNT_STORAGE_KEY = 'trackback.targetSongCount'
const MUSIC_SERVICE_STORAGE_KEY = 'trackback.musicService'
const DEFAULT_TARGET_SONG_COUNT = 10


const loadStoredTargetSongCount = () => {
  const count = parseInt(loadStored(TARGET_SONG_COUNT_STORAGE_KEY))
  return count > 0 ? count : DEFAULT_TARGET_SONG_COUNT
}

const rememberHostingChoice = (targetSongCount, musicServiceType) => {
  store(TARGET_SONG_COUNT_STORAGE_KEY, String(targetSongCount))
  store(MUSIC_SERVICE_STORAGE_KEY, musicServiceType)
}

const hostOptionsAreOpen = () => !document.getElementById('gameConfigBox').hidden

let musicServicesLoadedFrom = null

async function ensureMusicServiceChoice () {
  if (musicServicesLoadedFrom !== serverUrl) {
    await loadMusicServiceChoice(loadStored(MUSIC_SERVICE_STORAGE_KEY))
    musicServicesLoadedFrom = serverUrl
  }
}

function fillHostOptions (name, targetSongCount) {
  document.getElementById('sessionNameInput').value = name
  document.getElementById('targetSongCountInput').value = String(targetSongCount)
}

async function openHostOptions (error = '') {
  const errorLine = document.getElementById('hostOptionsError')
  errorLine.textContent = error
  errorLine.hidden = !error
  if (hostOptionsAreOpen()) {
    return
  }
  serverUrl = getServerUrl()
  await ensureMusicServiceChoice()
  const nameInput = document.getElementById('sessionNameInput')
  if (!nameInput.value) {
    const name = document.getElementById('username').value.trim()
    fillHostOptions(name ? `Game-by-${name}` : '', loadStoredTargetSongCount())
  }
  document.getElementById('gameConfigBox').hidden = false
  document.getElementById('hostOptionsBtn').setAttribute('aria-expanded', 'true')
}

function readHostOptions () {
  const targetSongCount = parseInt(
    document.getElementById('targetSongCountInput').value.trim()
  )
  if (isNaN(targetSongCount) || targetSongCount <= 0) {
    alert('⚠️ Please enter a valid number greater than 0 for songs!')
    return null
  }

  const name = document.getElementById('sessionNameInput').value.trim()
  if (!name) {
    alert('Please enter a Game Session Name!')
    return null
  }
  if (!isValidSessionName(name)) {
    alert(
      `Game Session Names can have up to ${SESSION_NAME_MAX_LENGTH} letters, digits, "_", "-" and single spaces.`
    )
    return null
  }
  return { name, targetSongCount }
}

async function hostGame () {
  serverUrl = getServerUrl()
  username = readUsername()
  if (!username) {
    return
  }
  await ensureMusicServiceChoice()
  const nameInput = document.getElementById('sessionNameInput')
  if (!hostOptionsAreOpen()) {
    fillHostOptions(`Game-by-${username}`, loadStoredTargetSongCount())
  } else if (!nameInput.value.trim()) {
    nameInput.value = `Game-by-${username}`
  }
  const options = readHostOptions()
  if (!options) {
    return
  }
  sessionName = options.name
  const musicServiceType = selectedMusicService()

  if (musicServiceType === 'spotify') {
    // The Spotify callback creates the Game Session and redirects back with a
    // join link, so the Host lands in the Lobby in this tab. The callback may
    // land on another origin, so remember the choice before leaving.
    storeUsername(username)
    rememberHostingChoice(options.targetSongCount, musicServiceType)
    const stateParam = encodeURIComponent(
      JSON.stringify({
        game_id: sessionName,
        target_song_count: options.targetSongCount,
        username
      })
    )
    window.location.assign(`${serverUrl}/spotify-login?state=${stateParam}`)
    return
  }

  try {
    const res = await fetch(`${serverUrl}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: sessionName,
        target_song_count: options.targetSongCount,
        music_service_type: musicServiceType
      })
    })
    const data = await res.json()

    if (!res.ok) {
      handleHttpError(data, '❌ Failed to create game')
      if (res.status === 409 || hostOptionsAreOpen()) {
        await openHostOptions(describeHttpError(data))
      }
      return
    }
  } catch (err) {
    console.error('❌ Failed to create music game:', err)
    log('❌ Failed to create game: the server could not be reached.')
    return
  }
  rememberHostingChoice(options.targetSongCount, musicServiceType)
  document.getElementById('gameConfigBox').hidden = true
  isHost = true

  await joinSession(sessionName)
}

document.getElementById('hostGameBtn').onclick = () => hostGame()
document.getElementById('hostOptionsBtn').onclick = () => openHostOptions()

document.getElementById('joinGameBtn').onclick = async () => {
  serverUrl = getServerUrl()
  username = readUsername()
  if (!username) {
    return
  }

  const sessions = await fetchJoinableSessions()
  if (!sessions) {
    return
  }

  if (!sessions.length) {
    alert('❌ No game sessions available to join.')
    return
  }

  if (sessions.length === 1) {
    await joinSession(sessions[0])
    return
  }

  document.getElementById('controls-new-or-join').hidden = true
  showSessionChoice(sessions)
}

document.getElementById('lobbyQrToggleBtn').onclick = () => toggleLobbyQrSize()

document.getElementById('startGameBtn').onclick = async () => {
  serverUrl = getServerUrl()

  try {
    const res = await fetch(`${serverUrl}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: sessionName })
    })
    const data = await res.json()
    if (!res.ok) {
      handleHttpError(data, '❌ Failed to start game')
      return
    }

    log(`🎮 ${data.message || 'Game started!'}`)
  } catch (err) {
    console.error('❌ Failed to start game:', err)
  }

  document.getElementById('controls-start').hidden = true
  hideLobbyQr()
  document.getElementById('timelineHeader').style.display = 'block'
  document.getElementById('songTimeline').style.display = 'block'
  document.getElementById('songCount').style.display = 'block'
}

const setupDragDrop = () => {
  const timeline = document.getElementById('songTimeline')
  const newSongContainer = document.getElementById('newSongContainer')

  new Sortable(timeline, {
    group: 'songs',
    animation: 150,
    sort: true,
    draggable: '.song-entry',
    filter: ':not(#new-song)',
    preventOnFilter: true,
    scroll: true,
    scrollSensitivity: 300,
    scrollSpeed: 5,
    onAdd: evt => {
      if (evt.item.id === 'new-song') {
        const newIndex = evt.newIndex

        evt.item.remove()

        socket.send(JSON.stringify({ type: 'guess', index: newIndex }))

        Sortable.get(timeline).option('disabled', true)
        Sortable.get(newSongContainer).option('disabled', true)
      }
    },
    onStart: () => {
      timeline.classList.add('drag-active')
    },
    onEnd: () => {
      timeline.classList.remove('drag-active')
    }
  })

  new Sortable(newSongContainer, {
    group: 'songs',
    sort: false
  })
}
