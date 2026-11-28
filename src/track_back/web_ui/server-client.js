// The only code that knows server URLs, HTTP and WebSocket details. Every HTTP
// call resolves to { data } or { error, status }, where `error` is readable
// text and `status` is the HTTP status if the server answered. Calls never throw.

const UNREACHABLE = 'the server could not be reached.'
const MAX_RECONNECT_ATTEMPTS = 10
const RECONNECT_BACKOFF = 2000
const PING_INTERVAL = 10000

// Resolves to true if the server's configuration script loaded. Without it,
// the server URL comes from the field the Server Operator or Player types in.
export function loadServerConfig () {
  return new Promise(resolve => {
    const script = document.createElement('script')
    script.src = 'server_config.js'
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.head.appendChild(script)
  })
}

export function serverUrl () {
  if (window.TRACK_BACK_CONFIG?.TRACK_BACK_SERVER_URL) {
    return window.TRACK_BACK_CONFIG.TRACK_BACK_SERVER_URL
  }
  const input = document.getElementById('server')
  return input?.value?.trim()?.replace(/\/+$/, '') || ''
}

// The server sends either full URLs or paths on itself, which start with "/".
export const resolveServerUrl = url =>
  url.startsWith('/') ? `${serverUrl()}${url}` : url

export const joinQrUrl = sessionName =>
  `${serverUrl()}/join-qr.svg?session=${encodeURIComponent(sessionName)}`

export const spotifyLoginUrl = ({ sessionName, targetSongCount, username }) => {
  const state = JSON.stringify({
    game_id: sessionName,
    target_song_count: targetSongCount,
    username
  })
  return `${serverUrl()}/spotify-login?state=${encodeURIComponent(state)}`
}

const describeHttpError = data => {
  const detail = data?.detail
  if (Array.isArray(detail)) {
    return detail.map(d => d.msg).join('; ')
  }
  return detail || 'Unknown error'
}

async function request (path, body) {
  const options = body === undefined
    ? {}
    : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      }
  let res
  try {
    res = await fetch(`${serverUrl()}${path}`, options)
  } catch (err) {
    console.error(`❌ Request to ${path} failed:`, err)
    return { error: UNREACHABLE }
  }
  let data
  try {
    data = await res.json()
  } catch (err) {
    console.error(`❌ Response from ${path} is not JSON:`, err)
    return {
      error: `the server sent an unexpected response (HTTP ${res.status}).`,
      status: res.status
    }
  }
  if (!res.ok) {
    return { error: describeHttpError(data), status: res.status }
  }
  return { data }
}

// An older server without this endpoint answers with status 404.
export const loadMusicServices = () => request('/music-services')

export async function listSessions () {
  const result = await request('/list-sessions')
  return result.error ? result : { data: result.data.sessions || [] }
}

export const createSession = ({ sessionName, targetSongCount, musicServiceType }) =>
  request('/create', {
    game_id: sessionName,
    target_song_count: targetSongCount,
    music_service_type: musicServiceType
  })

export const joinSession = (sessionName, username) =>
  request('/join', { game_id: sessionName, user_name: username })

export const startSession = sessionName =>
  request('/start', { game_id: sessionName })

// Opens the WebSocket for a Game Session and Username, and keeps it open:
// a keepalive ping, reconnecting with linear backoff, and reconnecting when
// the device comes back online. `onNotice` gets readable connection news,
// `onMessage` each server message. Returns { send }.
export function connect (sessionName, username, { onOpen, onMessage, onNotice }) {
  const url = new URL(serverUrl(), window.location.href)
  const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${url.host}/ws/${encodeURIComponent(
    sessionName
  )}/${encodeURIComponent(username)}`

  let socket
  let pingInterval = null
  let reconnectTimer = null
  let reconnectAttempts = 0

  const stopTimers = () => {
    clearInterval(pingInterval)
    pingInterval = null
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  const open = () => {
    stopTimers()
    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      onOpen?.()
      onNotice('🔌 Connected to game session.')
      reconnectAttempts = 0
      clearInterval(pingInterval)
      pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL)
    }

    socket.onerror = e => {
      console.error('🚨 WebSocket error:', e)
      onNotice('🚨 WebSocket encountered an error.')
    }

    socket.onmessage = event => {
      try {
        onMessage(JSON.parse(event.data))
      } catch (e) {
        console.error('❌ Error parsing WebSocket message:', e)
        onNotice('❌ Received invalid data from server.')
      }
    }

    socket.onclose = () => {
      onNotice('❌ Connection closed. Attempting to reconnect...')
      stopTimers()
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++
        reconnectTimer = setTimeout(() => {
          onNotice(`🔁 Reconnecting attempt ${reconnectAttempts}...`)
          open()
        }, RECONNECT_BACKOFF * reconnectAttempts)
      } else {
        onNotice('❌ Max reconnect attempts reached. Please reload the page.')
      }
    }
  }

  window.addEventListener('online', () => {
    if (socket.readyState === WebSocket.CLOSED) {
      onNotice('🌐 Network back online. Reconnecting WebSocket...')
      open()
    }
  })

  open()

  return {
    send: message => socket.send(JSON.stringify(message))
  }
}
