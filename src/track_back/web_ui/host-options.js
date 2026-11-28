// Host Options: the Game Setup panel, its summary strip, the Music Service
// line and picker, the default Game Session Name and the remembered choices.

import { isValidSessionName, sessionNameMaxLength } from './names.js'
import * as server from './server-client.js'
import { MUSIC_SERVICE_KEY, TARGET_SONG_COUNT_KEY, loadStored, store } from './storage.js'

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

const targetSongCountInput = document.getElementById('targetSongCountInput')

targetSongCountInput.addEventListener('input', () => {
  let value = targetSongCountInput.value.trim()

  if (!/^\d+$/.test(value) || parseInt(value) <= 0) {
    targetSongCountInput.value = ''
  }
})

// Hosting: "Host a Game" creates the Game Session with the Host Options, which
// start as these defaults. The Host Options strip under the button summarises
// them and opens and closes the panel for editing them.
const DEFAULT_TARGET_SONG_COUNT = 10

const defaultSessionName = name => `Game-by-${name}`

const loadStoredTargetSongCount = () => {
  const count = parseInt(loadStored(TARGET_SONG_COUNT_KEY))
  return count > 0 ? count : DEFAULT_TARGET_SONG_COUNT
}

export function rememberHostingChoice ({ targetSongCount, musicServiceType }) {
  store(TARGET_SONG_COUNT_KEY, String(targetSongCount))
  store(MUSIC_SERVICE_KEY, musicServiceType)
  showHostOptionsError('')
}

export const hostOptionsAreOpen = () => !document.getElementById('gameConfigBox').hidden

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
      loadStored(MUSIC_SERVICE_KEY)
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
export async function prepareHostOptions () {
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

export const closeHostOptions = () => setHostOptionsOpen(false)

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
    return `Game Session Names can have up to ${sessionNameMaxLength()} letters, digits, "_", "-" and single spaces.`
  }
  return ''
}

// Shows a problem with hosting inside Host Options, opening them if needed.
export const showHostingProblem = error => openHostOptions(error)

// Returns { sessionName, targetSongCount, musicServiceType }, or null after
// telling the Host what is missing.
export async function readHostingChoice () {
  if (!(await ensureMusicServiceChoice())) {
    return null
  }
  fillDefaultSessionName()
  const problem = hostOptionsProblem()
  if (problem) {
    await openHostOptions(problem)
    return null
  }
  return {
    sessionName: document.getElementById('sessionNameInput').value.trim(),
    targetSongCount: parseInt(
      document.getElementById('targetSongCountInput').value.trim()
    ),
    musicServiceType: selectedMusicService()
  }
}

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
