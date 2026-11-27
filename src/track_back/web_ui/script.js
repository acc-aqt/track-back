import * as hostOptions from './host-options.js'
import { USERNAME_MAX_LENGTH, isValidUsername } from './names.js'
import { createRoundFlow } from './round-flow.js'
import * as screen from './screen.js'
import * as server from './server-client.js'
import { USERNAME_KEY, loadStored, store } from './storage.js'

let connection
let sessionName
let username
let isHost = false

// Without the server's configuration script, ask for the server URL.
server.loadServerConfig().then(loaded => {
  document.getElementById('controls-server').hidden = loaded
  startApp()
})

function startApp () {
  console.log('🌐 Using server URL:', server.serverUrl())
  prefillStoredUsername()
  hostOptions.prepareHostOptions()
  handleJoinLink()
}

function prefillStoredUsername () {
  const input = document.getElementById('username')
  if (!input.value) {
    input.value = loadStored(USERNAME_KEY)
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
  screen.showScreen('setup', { sessionChoice: true })
  document.getElementById('joinGameTitle').textContent =
    'Enter your username to join'
  document.getElementById('username').focus()
}

const log = msg => {
  const logBox = document.getElementById('log')
  if (logBox.classList.contains('log-empty')) {
    logBox.classList.remove('log-empty')
    logBox.textContent = ''
  }
  logBox.textContent += msg + '\n'
  logBox.scrollTop = logBox.scrollHeight
}

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

const roundFlow = createRoundFlow({
  log,
  sendGuess: index => connection.send({ type: 'guess', index })
})

const serverMessageHandlers = {
  your_turn: data => roundFlow.guessRequest(data),
  guess_result: data => roundFlow.guessResult(data),
  welcome: data => log(`👋🏻 ${data.message}`),
  player_joined: data => log(`👋🏻 ${data.message}`),
  player_rejoined: data => {
    if (data.user_name === username) {
      roundFlow.rejoin(data.song_list)
    } else {
      log(`👋🏻 ${data.message}`)
    }
  },
  error: data => log(`🚨 Error: ${data.message}`),
  other_player_guess: data => log(`🧑🏽‍🎤 ${data.message}`),
  game_over: data =>
    roundFlow.gameOver({ winner: data.winner, winnerIsYou: data.winner === username }),
  user_disconnected: data => log(`❌ ${data.message}`)
}

function connectWebSocket () {
  connection = server.connect(sessionName, username, {
    onMessage: handleServerMessage,
    onNotice: log
  })
}

function handleServerMessage (data) {
  if (Object.hasOwn(serverMessageHandlers, data.type)) {
    serverMessageHandlers[data.type](data)
  } else {
    log(`Unknown message type: ${data.type}.`)
  }
}

async function fetchJoinableSessions () {
  const { data, error } = await server.listSessions()
  if (error) {
    log(`❌ Failed to fetch game sessions: ${error}`)
    return null
  }
  return data
}

function showSessionChoice (sessions) {
  document.getElementById('joinGameTitle').textContent = 'Select a Game Session to join'

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
    screen.showScreen('lobby', { isHost })
  }
  return success
}

async function joinGame () {
  username = readUsername()
  if (!username) {
    return false
  }
  const { error } = await server.joinSession(sessionName, username)
  if (error) {
    log(`❌ Failed to join game: ${error}`)
    return false
  }

  log(`✅ Joined game: ${sessionName}`)
  store(USERNAME_KEY, username)
  connectWebSocket()
  screen.loadLobbyQr(server.joinQrUrl(sessionName))
  return true
}

// A failed lookup counts as not listed; the server rejects taken names anyway.
async function isListedSessionName (name) {
  const { data, error } = await server.listSessions()
  return !error && data.includes(name)
}

async function hostGame () {
  username = readUsername()
  if (!username) {
    return
  }
  const choice = await hostOptions.readHostingChoice()
  if (!choice) {
    return
  }
  sessionName = choice.sessionName

  if (choice.musicServiceType === 'spotify') {
    // Catch a taken name before the Spotify login; the callback still rejects
    // names that /list-sessions doesn't show (running Game Sessions).
    if (await isListedSessionName(sessionName)) {
      const error = `Game session '${sessionName}' already exists. Choose a different name.`
      log(`❌ Failed to create Game Session: ${error}`)
      await hostOptions.showHostingProblem(error)
      return
    }
    // The Spotify callback creates the Game Session and redirects back with a
    // join link, so the Host lands in the Lobby in this tab. The callback may
    // land on another origin, so remember the choice before leaving.
    store(USERNAME_KEY, username)
    hostOptions.rememberHostingChoice(choice)
    window.location.assign(
      server.spotifyLoginUrl({
        sessionName,
        targetSongCount: choice.targetSongCount,
        username
      })
    )
    return
  }

  const { error, status } = await server.createSession(choice)
  if (error) {
    log(`❌ Failed to create Game Session: ${error}`)
    if (status === 409 || (status !== undefined && hostOptions.hostOptionsAreOpen())) {
      await hostOptions.showHostingProblem(error)
    }
    return
  }
  hostOptions.rememberHostingChoice(choice)
  hostOptions.closeHostOptions()
  isHost = true

  await joinSession(sessionName)
}

document.getElementById('hostGameBtn').onclick = () => hostGame()

document.getElementById('joinGameBtn').onclick = async () => {
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

  showSessionChoice(sessions)
  screen.showScreen('setup', { hostAndJoin: false, sessionChoice: true })
}

document.getElementById('startGameBtn').onclick = async () => {
  const { data, error } = await server.startSession(sessionName)
  if (error) {
    log(`❌ Failed to start game: ${error}`)
    return
  }
  log(`🎮 ${data.message || 'Game started!'}`)
  // The first Round's Song may already be on screen.
  if (screen.currentScreen() === 'lobby') {
    screen.showScreen('playing')
  }
}
