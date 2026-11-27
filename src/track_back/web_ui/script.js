'use strict'

let socket
let gameId
let username
let isHostingSpotifySession = false

let serverUrl = ''

let pingInterval = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10

const NAME_PATTERN = /^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u
const USERNAME_MAX_LENGTH = 20
const GAME_ID_MAX_LENGTH = 40
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
}

const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', '']
if (!LOCAL_HOSTNAMES.includes(window.location.hostname)) {
  document.querySelector('#musicServiceDropdown option[value="mock"]')?.remove()
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

const isValidGameId = id =>
  id.length <= GAME_ID_MAX_LENGTH && NAME_PATTERN.test(id)

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

function showTimeline (list) {
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
    gameId
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
async function listAndChooseGameSessions () {
  try {
    document.getElementById('joinGameConfigBox').hidden = false

    const res = await fetch(`${serverUrl}/list-sessions`)
    const data = await res.json()
    if (!res.ok) {
      handleHttpError(data)
      return
    }

    const sessions = data.sessions || []
    const dropdown = document.getElementById('sessionDropdown')
    const joinButton = document.getElementById('joinSelectedSessionBtn')

    dropdown.innerHTML = ''

    if (sessions.length === 0) {
      alert('❌ No available game sessions.')
      return
    }

    sessions.forEach((sessionId, index) => {
      const option = document.createElement('option')
      option.value = sessionId
      option.textContent = `${index + 1}. ${sessionId}`
      dropdown.appendChild(option)
    })

    joinButton.onclick = async () => {
      const selectedGameId = dropdown.value
      if (!selectedGameId) {
        alert('❌ Please select a session.')
        return
      }
      gameId = selectedGameId
      const success = await joinGame()
      if (success) {
        document.getElementById('controls-waiting-for-start').hidden = false
      }
    }
  } catch (err) {
    console.error('❌ Failed to fetch sessions:', err)
    alert('⚠️ Failed to fetch game sessions.')
  }
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
      body: JSON.stringify({ game_id: gameId, user_name: username })
    })

    const data = await res.json()

    if (!res.ok) {
      handleHttpError(data, '❌ Failed to join game')
      return false
    }

    log(`✅ Joined game: ${gameId}`)
    connectWebSocket()
    if (isHostingSpotifySession) {
      document.getElementById('controls-start').hidden = false
    }
    document.getElementById('joinGameConfigBox').hidden = true
    return true
  } catch (err) {
    console.error('❌ Failed to join game:', err)
    return false
  }
}

async function configureGame () {
  username = readUsername()
  if (!username) {
    return
  }
  document.getElementById('gameConfigBox').hidden = false

  document.getElementById('controls-new-or-join').hidden = true

  document.getElementById('gameIdInput').value = `Game-by-${username}`
}

async function createGame () {
  serverUrl = getServerUrl()
  username = readUsername()
  if (!username) {
    return
  }
  const songCountInput = document
    .getElementById('targetSongCountInput')
    .value.trim()
  const targetSongCount = parseInt(songCountInput)

  if (isNaN(targetSongCount) || targetSongCount <= 0) {
    alert('⚠️ Please enter a valid number greater than 0 for songs!')
    return
  }

  gameId = document.getElementById('gameIdInput').value.trim()

  if (!gameId) {
    alert('Please enter a game ID!')
    return
  }
  if (!isValidGameId(gameId)) {
    alert(
      `Game IDs can have up to ${GAME_ID_MAX_LENGTH} letters, digits, "_", "-" and single spaces.`
    )
    return
  }

  const musicServiceType = document.getElementById('musicServiceDropdown').value

  if (musicServiceType === 'spotify') {
    // ✨ Spotify: first login
    const stateObject = {
      game_id: gameId,
      target_song_count: targetSongCount
    }

    const stateParam = encodeURIComponent(JSON.stringify(stateObject))

    const loginUrl = `${serverUrl}/spotify-login?state=${stateParam}`

    document.getElementById('joinGameBtn').innerHTML =
      'After login to Spotify: 📻&thinsp;🔑<br>Join the new game session 👋🏻'

    document.getElementById('controls-new-or-join').hidden = false
    document.getElementById('joinGameTitle').style.display = 'none'
    document.getElementById('sessionDropdown').style.display = 'none'

    document.getElementById('joinGameBtn').style.display = 'block'
    document.getElementById('controls-start').hidden = true
    document.getElementById('gameConfigBox').hidden = true

    document.getElementById('configureGameBtn').style.display = 'none'

    isHostingSpotifySession = true
    window.open(loginUrl, '_blank')

    log(`🎮 Created new spotify game session: ${gameId}`)

    // user returns later and clicks Join
  } else {
    try {
      const res = await fetch(`${serverUrl}/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          target_song_count: targetSongCount,
          music_service_type: musicServiceType
        })
      })
      const data = await res.json()

      if (!res.ok) {
        handleHttpError(data, '❌ Failed to create game')
        return
      }
    } catch (err) {
      console.error('❌ Failed to create music game:', err)
      return
    }
    document.getElementById('gameConfigBox').hidden = true
    document.getElementById('controls-start').hidden = false

    await joinGame()
  }
}

document.getElementById('configureGameBtn').onclick = () => configureGame()
document.getElementById('createGameBtn').onclick = () => createGame()

document.getElementById('joinGameBtn').onclick = async () => {
  serverUrl = getServerUrl()
  username = readUsername()
  if (!username) {
    return
  }

  const res = await fetch(`${serverUrl}/list-sessions`)
  const data = await res.json()

  if (!res.ok) {
    handleHttpError(data)
    return
  }

  if (!data.sessions.length) {
    alert('❌ No game sessions available to join.')
    return
  }

  document.getElementById('controls-new-or-join').hidden = true

  if (isHostingSpotifySession) {
    await joinGame()
    return
  }
  await listAndChooseGameSessions()
}

document.getElementById('startGameBtn').onclick = async () => {
  serverUrl = getServerUrl()

  try {
    const res = await fetch(`${serverUrl}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId })
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
