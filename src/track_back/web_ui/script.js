import { createRoundFlow } from './round-flow.js'
import * as screen from './screen.js'
import * as server from './server-client.js'

let connection
let sessionName
let username
let isHost = false

const NAME_PATTERN = /^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u
const USERNAME_MAX_LENGTH = 20
const SESSION_NAME_MAX_LENGTH = 40

// Without the server's configuration script, ask for the server URL.
server.loadServerConfig().then(loaded => {
  document.getElementById('controls-server').hidden = loaded
  startApp()
})

function startApp () {
  console.log('🌐 Using server URL:', server.serverUrl())
  prefillStoredUsername()
  prepareHostOptions()
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

function prefillStoredUsername () {
  const input = document.getElementById('username')
  if (!input.value) {
    input.value = loadStored(USERNAME_STORAGE_KEY)
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

// Music Service choice in Game Setup: "Music: <service>" and a change button.
const MUSIC_SERVICE_LABELS = {
  spotify: 'Spotify 📻🎶',
  applemusic: 'Apple Music 🍎🎶',
  mock: 'Mock Music Service'
}

// Shorter names for the Host Options strip, which has little room.
const MUSIC_SERVICE_SHORT_LABELS = {
  spotify: 'Spotify',
  applemusic: 'Apple Music',
  mock: 'Mock'
}

// Older servers have no /music-services; offer the real services as before.
const OLDER_SERVER_MUSIC_SERVICES = {
  default: 'spotify',
  available: ['spotify', 'applemusic'],
  fromOlderServer: true
}

// Returns null if the Music Services can't be fetched.
async function fetchMusicServices () {
  const { data, error, status } = await server.loadMusicServices()
  if (status === 404) {
    return OLDER_SERVER_MUSIC_SERVICES
  }
  if (error) {
    console.error('❌ Failed to fetch music services:', error)
    return null
  }
  return data
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
  updateHostOptionsSummary()
}

async function loadMusicServiceChoice (preferred = null) {
  const services = await fetchMusicServices()
  if (services) {
    showMusicServiceChoice(services, preferred)
  }
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

document.getElementById('musicServiceDropdown').onchange = () => {
  const dropdown = document.getElementById('musicServiceDropdown')
  document.getElementById('musicServiceName').textContent =
    MUSIC_SERVICE_LABELS[dropdown.value] || dropdown.value
  updateHostOptionsSummary()
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
  store(USERNAME_STORAGE_KEY, username)
  connectWebSocket()
  screen.loadLobbyQr(server.joinQrUrl(sessionName))
  return true
}

// Hosting: "Host a Game" creates the Game Session with the Host Options, which
// start as these defaults. The Host Options strip under the button summarises
// them and opens and closes the panel for editing them.
const TARGET_SONG_COUNT_STORAGE_KEY = 'trackback.targetSongCount'
const MUSIC_SERVICE_STORAGE_KEY = 'trackback.musicService'
const DEFAULT_TARGET_SONG_COUNT = 10

const defaultSessionName = name => `Game-by-${name}`

const loadStoredTargetSongCount = () => {
  const count = parseInt(loadStored(TARGET_SONG_COUNT_STORAGE_KEY))
  return count > 0 ? count : DEFAULT_TARGET_SONG_COUNT
}

const rememberHostingChoice = (targetSongCount, musicServiceType) => {
  store(TARGET_SONG_COUNT_STORAGE_KEY, String(targetSongCount))
  store(MUSIC_SERVICE_STORAGE_KEY, musicServiceType)
}

const hostOptionsAreOpen = () => !document.getElementById('gameConfigBox').hidden

const usernameSessionName = () => {
  const name = document.getElementById('username').value.trim()
  return name ? defaultSessionName(name) : ''
}

let musicServicesLoadedFrom = null
let musicServicesLoading = null

// Callers share one load per server, so a later load can't reset the Music
// Service the Host picked after an earlier one. A failed load can be retried.
function loadMusicServicesOnce () {
  if (musicServicesLoading?.serverUrl !== server.serverUrl()) {
    const url = server.serverUrl()
    const promise = loadMusicServiceChoice(
      loadStored(MUSIC_SERVICE_STORAGE_KEY)
    ).then(services => {
      if (services) {
        musicServicesLoadedFrom = url
        updateHostOptionsSummary()
      } else if (musicServicesLoading?.promise === promise) {
        musicServicesLoading = null
      }
      return Boolean(services)
    })
    musicServicesLoading = { serverUrl: url, promise }
  }
  return musicServicesLoading.promise
}

// Returns false if the Music Services could not be loaded. `quiet` skips
// telling the Host, for the load in the background when the page opens.
async function ensureMusicServiceChoice ({ quiet = false } = {}) {
  if (musicServicesLoadedFrom === server.serverUrl()) {
    return true
  }
  const loaded = await loadMusicServicesOnce()
  if (!loaded && !quiet) {
    alert('⚠️ Failed to fetch the Music Services. Please try again.')
  }
  return loaded
}

// The default name follows the Username until the Host edits it.
let filledDefaultSessionName = ''

function fillDefaultSessionName () {
  const nameInput = document.getElementById('sessionNameInput')
  const name = nameInput.value.trim()
  if (!name || name === filledDefaultSessionName) {
    nameInput.value = usernameSessionName()
    filledDefaultSessionName = nameInput.value
  }
}

function hostOptionsSummaryParts () {
  const count = parseInt(document.getElementById('targetSongCountInput').value)
  const loaded =
    musicServicesLoadedFrom !== null &&
    musicServicesLoadedFrom === server.serverUrl()
  const service = loaded ? selectedMusicService() : ''
  return [
    count > 0 ? `${count} ${count === 1 ? 'song' : 'songs'}` : '',
    service ? MUSIC_SERVICE_SHORT_LABELS[service] || service : ''
  ].filter(Boolean)
}

// The name keeps its own case, so it gets a span the strip doesn't uppercase.
function updateHostOptionsSummary () {
  const children = hostOptionsSummaryParts().map(part => `${part} · `)
  const name = document.getElementById('sessionNameInput').value.trim()
  if (name && name !== usernameSessionName()) {
    const nameSpan = document.createElement('span')
    nameSpan.className = 'host-options-name'
    nameSpan.textContent = name
    children.push(nameSpan, ' · ')
  }
  document.getElementById('hostOptionsSummary').replaceChildren(...children)
}

// A count the browser restored into the field wins over the stored one.
async function prepareHostOptions () {
  const countInput = document.getElementById('targetSongCountInput')
  if (countInput.value === countInput.defaultValue) {
    countInput.value = String(loadStoredTargetSongCount())
  }
  updateHostOptionsSummary()
  await ensureMusicServiceChoice({ quiet: true })
}

function showHostOptionsError (error) {
  const errorBox = document.getElementById('hostOptionsError')
  errorBox.textContent = error
  errorBox.hidden = !error
}

function setHostOptionsOpen (open) {
  document.getElementById('gameConfigBox').hidden = !open
  document
    .getElementById('hostOptionsBtn')
    .setAttribute('aria-expanded', String(open))
  document.getElementById('hostOptionsArrow').textContent = open ? '▴' : '▾'
}

async function openHostOptions (error = '') {
  showHostOptionsError(error)
  if (hostOptionsAreOpen()) {
    return
  }
  if (!(await ensureMusicServiceChoice())) {
    return
  }
  fillDefaultSessionName()
  updateHostOptionsSummary()
  setHostOptionsOpen(true)
}

async function toggleHostOptions () {
  if (hostOptionsAreOpen()) {
    setHostOptionsOpen(false)
    return
  }
  await openHostOptions()
}

function hostOptionsProblem () {
  const targetSongCount = parseInt(
    document.getElementById('targetSongCountInput').value.trim()
  )
  if (isNaN(targetSongCount) || targetSongCount <= 0) {
    return 'Please enter a valid number greater than 0 for songs!'
  }
  const name = document.getElementById('sessionNameInput').value.trim()
  if (!name) {
    return 'Please enter a Game Session Name!'
  }
  if (!isValidSessionName(name)) {
    return `Game Session Names can have up to ${SESSION_NAME_MAX_LENGTH} letters, digits, "_", "-" and single spaces.`
  }
  return ''
}

// Returns null after showing the problem inside Host Options.
async function readHostOptions () {
  const problem = hostOptionsProblem()
  if (problem) {
    await openHostOptions(problem)
    return null
  }
  return {
    name: document.getElementById('sessionNameInput').value.trim(),
    targetSongCount: parseInt(
      document.getElementById('targetSongCountInput').value.trim()
    )
  }
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
  if (!(await ensureMusicServiceChoice())) {
    return
  }
  fillDefaultSessionName()
  const options = await readHostOptions()
  if (!options) {
    return
  }
  sessionName = options.name
  const musicServiceType = selectedMusicService()

  if (musicServiceType === 'spotify') {
    // Catch a taken name before the Spotify login; the callback still rejects
    // names that /list-sessions doesn't show (running Game Sessions).
    if (await isListedSessionName(sessionName)) {
      const error = `Game session '${sessionName}' already exists. Choose a different name.`
      log(`❌ Failed to create Game Session: ${error}`)
      await openHostOptions(error)
      return
    }
    // The Spotify callback creates the Game Session and redirects back with a
    // join link, so the Host lands in the Lobby in this tab. The callback may
    // land on another origin, so remember the choice before leaving.
    store(USERNAME_STORAGE_KEY, username)
    rememberHostingChoice(options.targetSongCount, musicServiceType)
    showHostOptionsError('')
    window.location.assign(
      server.spotifyLoginUrl({
        sessionName,
        targetSongCount: options.targetSongCount,
        username
      })
    )
    return
  }

  const { error, status } = await server.createSession({
    sessionName,
    targetSongCount: options.targetSongCount,
    musicServiceType
  })
  if (error) {
    log(`❌ Failed to create Game Session: ${error}`)
    if (status === 409 || (status !== undefined && hostOptionsAreOpen())) {
      await openHostOptions(error)
    }
    return
  }
  rememberHostingChoice(options.targetSongCount, musicServiceType)
  showHostOptionsError('')
  setHostOptionsOpen(false)
  isHost = true

  await joinSession(sessionName)
}

document.getElementById('hostGameBtn').onclick = () => hostGame()
document.getElementById('hostOptionsBtn').onclick = () => toggleHostOptions()

document
  .getElementById('username')
  .addEventListener('input', () => fillDefaultSessionName())

for (const id of ['targetSongCountInput', 'sessionNameInput', 'username']) {
  document
    .getElementById(id)
    .addEventListener('input', () => updateHostOptionsSummary())
}

for (const id of [
  'targetSongCountInput',
  'sessionNameInput',
  'musicServiceDropdown'
]) {
  document
    .getElementById(id)
    .addEventListener('input', () => showHostOptionsError(''))
}

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
