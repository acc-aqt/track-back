let socket
let username
let currentGuessSong = null
let pauseAfterGuess = false
let queuedTurn = null

const WRONG_GUESS_DISPLAY_TIME = 3000 // How long the wrong guess stays visible
const FADE_DURATION = 1000 // Duration of fade-out animation

const log = msg => {
  const logBox = document.getElementById('log')
  logBox.textContent += msg + '\n'
  logBox.scrollTop = logBox.scrollHeight
}

const buildSongEntry = (song, id = '', extra = '') => {
  return `
    <div class="song-entry ${extra}" ${id ? `id="${id}"` : ''}>
      <img src="${
        song.album_cover_url
      }" alt="cover" class="song-cover" onerror="this.src='dummy-cover/cover1.png'" />
      <div class="song-details">
        <strong>${song.title}</strong> (${song.release_year})<br />
        by ${song.artist}
      </div>
    </div>
  `
}

const buildSongListHtml = (list, newSong) => {
  const entries = list.map(
    (s, i) => `
    <div class="song-entry" draggable="false" data-index="${i}">
      <img src="${s.album_cover_url}" alt="cover" class="song-cover" onerror="this.src='dummy-cover/cover1.png'" />
      <div class="song-details">
        <strong>${s.title}</strong> (${s.release_year})<br />
        by ${s.artist}
      </div>
    </div>
  `
  )

  const newEntry = `
    <div class="song-entry highlight" id="new-song">
      <img src="${newSong.album_cover_url}" alt="cover" class="song-cover"  onerror="this.src='dummy-cover/cover1.png'" />
      <div class="song-details">
        <strong>Drag the song to the right place in the timeline.</strong>
      </div>
    </div>
  `

  return newEntry + entries.join('')
}

document.getElementById('connectBtn').onclick = async () => {
  username = document.getElementById('username').value
  const serverInput = document
    .getElementById('server')
    .value.trim()
    .replace(/\/+\$/, '')

  if (!username || !serverInput) {
    alert('Please enter both server address and username.')
    return
  }

  let urlObj
  try {
    urlObj = new URL(serverInput)
  } catch (e) {
    alert('⚠️ Invalid server address.')
    return
  }

  const wsProtocol = urlObj.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${urlObj.host}/ws/${username}`

  function handleYourTurn (data) {
    if (pauseAfterGuess) {
      queuedTurn = data
      return
    }
    log(`🎮 It's your turn! Drag the new song into the right place.`)
    document.getElementById('songListHeader').style.display = 'block'
    document.getElementById('songTimeline').style.display = 'block'

    const list = data.song_list || []
    const dummyCovers = [
      'dummy-cover/cover1.png',
      'dummy-cover/cover2.png',
      'dummy-cover/cover3.png'
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

    document.getElementById('songTimeline').innerHTML = list
      .map(s => buildSongEntry(s))
      .join('')

    setupDragDrop(list.length)
  }

  function handleGuessResult (data) {
    log(`🎯 ${data.result.toUpperCase()}: ${data.message}`)
    const list = data.song_list || []

    const timeline = document.getElementById('songTimeline')

    // Always clear the new song container
    document.getElementById('newSongContainer').style.display = 'none'

    // Update the timeline first (without the guess)
    timeline.innerHTML = list.map(s => buildSongEntry(s)).join('')

    // If the guess was wrong, insert the incorrect guess at the user's chosen position
    if (data.result === 'wrong') {
      const wrongSong = data.last_song || {}
      const guessedIndex = data.last_index ?? 0

      const wrongSongHTML = `
            <div class="song-entry wrong-guess">
              <span class="wrong-label"></span>
              <img src="${wrongSong.album_cover_url}" alt="cover" class="song-cover" onerror="this.src='dummy-cover/cover1.png'" />
              <div class="song-details">
                <strong>${wrongSong.title}</strong> (${wrongSong.release_year})<br />
                by ${wrongSong.artist}
              </div>
            </div>
          `

      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = wrongSongHTML
      const wrongSongEl = tempDiv.firstElementChild

      const children = timeline.children

      if (guessedIndex >= 0 && guessedIndex < children.length) {
        timeline.insertBefore(wrongSongEl, children[guessedIndex])
      } else {
        timeline.appendChild(wrongSongEl)
      }

      // Fade out and remove after 5 seconds
      setTimeout(() => {
        wrongSongEl.classList.add('fade-out')
        setTimeout(() => {
          wrongSongEl.remove()
        }, FADE_DURATION)
      }, WRONG_GUESS_DISPLAY_TIME)

      log(`DATA ${data}`)

      pauseAfterGuess = true
      setTimeout(() => {
        pauseAfterGuess = false

        // If a turn came in while we were paused, now we handle it
        if (queuedTurn) {
          handleYourTurn(queuedTurn)
          queuedTurn = null
        }
      }, WRONG_GUESS_DISPLAY_TIME + FADE_DURATION)
    }
  }

  try {
    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      log(`🛰️ Connected as ${username}`)
      document.getElementById('game').style.display = 'block'
      document.getElementById('startGameBtn').style.display = 'inline-block'
    }

    socket.onerror = e => {
      console.error('🚨 WebSocket error:', e)
      log('🚨 Connection error')
    }

    socket.onmessage = event => {
      const data = JSON.parse(event.data)
      const type = data.type

      if (type === 'your_turn' && data.next_player === username) {
        handleYourTurn(data)
      } else if (type === 'guess_result' && data.player === username) {
        handleGuessResult(data)
      } else if (type === 'welcome') {
        log(`👋 ${data.message}`)
      } else if (type === 'error') {
        log(`🚨 Error: ${data.message}`)
      } else if (type === 'turn_result') {
        log(`🪄 ${data.player} played: ${data.message}`)
      } else if (type === 'game_over') {
        log(`🏁 Game Over! Winner: ${data.winner}`)
        document.getElementById('newSongContainer').style.display = 'none'

        const winnerHeader = document.getElementById('winnerHeader')
        const isYou = data.winner === username

        winnerHeader.innerHTML = isYou
          ? '🎉&thinsp;You win!&thinsp;🎉<br />👩🏻‍🎤&thinsp;🏆'
          : `Game over.<br />${data.winner} won the game.`

        winnerHeader.style.display = 'block'
      }
    }

    socket.onclose = () => {
      log('🔌 Connection closed.')
    }
  } catch (err) {
    console.error('❌ Failed to connect:', err)
  }
}

document.getElementById('startGameBtn').onclick = async () => {
  const serverInput = document
    .getElementById('server')
    .value.trim()
    .replace(/\/+\$/, '')
  let urlObj
  try {
    urlObj = new URL(serverInput)
  } catch (e) {
    alert('Invalid server address')
    return
  }

  const startUrl = `${urlObj.origin}/start`

  try {
    const res = await fetch(startUrl, { method: 'POST' })
    const data = await res.json()
    log(`🎮 ${data.message || 'Game started!'}`)
  } catch (err) {
    log('❌ Failed to start the game.')
  }

  document.getElementById('songListHeader').style.display = 'block'
  document.getElementById('songTimeline').style.display = 'block'
}

document.getElementById('stopServerBtn').onclick = async () => {
  const serverUrl = document
    .getElementById('server')
    .value.trim()
    .replace(/\/+\$/, '')
  let urlObj
  try {
    urlObj = new URL(serverUrl)
  } catch (e) {
    alert('Invalid server URL')
    return
  }

  const shutdownUrl = `${urlObj.origin}/shutdown`
  try {
    const res = await fetch(shutdownUrl, { method: 'POST' })
    const data = await res.json()
    log(`🛑 ${data.message}`)
  } catch (err) {
    log('❌ Failed to stop the server.')
  }
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
    onAdd: evt => {
      if (evt.item.id === 'new-song') {
        const newIndex = evt.newIndex
        log(`📤 Guess submitted: insert at index ${newIndex}`)

        // Remove the dragged song from the timeline immediately
        evt.item.remove()

        // Send the guess to the server
        socket.send(JSON.stringify({ type: 'guess', index: newIndex }))

        // Disable dragging
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
