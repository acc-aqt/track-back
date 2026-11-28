// Turns the game's server messages into what the Player sees: the new Song to
// place, the result of a Guess, the Timeline after a Rejoin and the Winner.
// After a wrong Guess it pauses, and a guess request arriving meanwhile waits.

import * as screen from './screen.js'
import { resolveServerUrl } from './server-client.js'

const WRONG_GUESS_DISPLAY_TIME = 2000
const FADE_DURATION = 1000
const FALLBACK_COVER = 'dummy-cover/cover1.webp'
const DUMMY_COVERS = [
  'dummy-cover/cover1.webp',
  'dummy-cover/cover2.webp',
  'dummy-cover/cover3.webp',
  'dummy-cover/cover4.webp',
  'dummy-cover/cover5.webp',
  'dummy-cover/cover6.webp'
]

// Spotify sends a full URL, Apple Music a path on the server.
const coverSrc = song => {
  const url = song.album_cover_url
  return url ? resolveServerUrl(url) : FALLBACK_COVER
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

const showSongCount = count => {
  document.getElementById('songCount').textContent = `Song count: ${count}`
}

function showTimeline (list) {
  screen.showScreen('playing')
  showSongCount(list.length)
  document
    .getElementById('songTimeline')
    .replaceChildren(...list.map(s => buildSongEntry(s)))
}

// Created once; enabled for each Round until its Guess is sent.
function createDragDrop (sendGuess) {
  const timeline = document.getElementById('songTimeline')
  const newSongContainer = document.getElementById('newSongContainer')

  const sortables = [
    new Sortable(timeline, {
      group: 'songs',
      animation: 150,
      sort: true,
      disabled: true,
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
          sendGuess(newIndex)
          setEnabled(false)
        }
      },
      onStart: () => {
        timeline.classList.add('drag-active')
      },
      onEnd: () => {
        timeline.classList.remove('drag-active')
      }
    }),
    new Sortable(newSongContainer, {
      group: 'songs',
      sort: false,
      disabled: true
    })
  ]

  function setEnabled (enabled) {
    for (const sortable of sortables) {
      sortable.option('disabled', !enabled)
    }
  }

  return { setEnabled }
}

function showWrongGuess (data) {
  const timeline = document.getElementById('songTimeline')
  const guessedIndex = Number(data.last_index ?? 0)

  const wrongSongEl = buildSongEntry(data.last_song || {}, 'wrong-guess')
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
}

// `sendGuess(index)` sends the Player's Guess to the server.
export function createRoundFlow ({ log, sendGuess }) {
  const dragDrop = createDragDrop(sendGuess)
  let paused = false
  let queuedGuessRequest = null
  let pauseTimer = null
  let over = false

  function guessRequest (data) {
    if (over) {
      return
    }
    if (paused) {
      queuedGuessRequest = data
      return
    }

    showTimeline(data.song_list || [])

    const randomCover =
      DUMMY_COVERS[Math.floor(Math.random() * DUMMY_COVERS.length)]
    document.getElementById('newSongContainer').innerHTML = `
    <div class="song-entry highlight" id="new-song">
      <img src="${randomCover}" alt="cover" class="song-cover" />
      <div class="song-details">
        <strong>Drag the song to the right place in the timeline.</strong>
      </div>
    </div>
  `
    screen.showScreen('playing', { newSong: true })
    dragDrop.setEnabled(true)
  }

  function pauseAfterWrongGuess () {
    paused = true
    pauseTimer = setTimeout(() => {
      paused = false
      if (queuedGuessRequest) {
        const data = queuedGuessRequest
        queuedGuessRequest = null
        guessRequest(data)
      }
    }, WRONG_GUESS_DISPLAY_TIME + FADE_DURATION)
  }

  function guessResult (data) {
    const list = data.song_list || []
    if (data.result === 'correct') {
      log(`✅ Guess was correct: ${data.message}`)
      showSongCount(list.length)
    } else {
      log(`❌ Guess was wrong: ${data.message}`)
    }

    screen.showScreen('playing')
    document
      .getElementById('songTimeline')
      .replaceChildren(...list.map(s => buildSongEntry(s)))

    if (data.result === 'wrong') {
      showWrongGuess(data)
      pauseAfterWrongGuess()
    }
  }

  function rejoin (songList) {
    showTimeline(songList || [])
    log('👋🏻 Welcome back! Waiting for the others to guess.')
  }

  function gameOver ({ winner, winnerIsYou }) {
    over = true
    clearTimeout(pauseTimer)
    queuedGuessRequest = null
    dragDrop.setEnabled(false)
    log(`🏁 Game Over! Winner: ${winner}`)
    screen.showScreen('gameOver')
    document.getElementById('winnerHeader').replaceChildren(
      ...(winnerIsYou
        ? ['🎉 You win! 🎉', document.createElement('br'), '👩🏻‍🎤 🏆']
        : ['Game over.', document.createElement('br'), `${winner} won the game.`])
    )
  }

  return { guessRequest, guessResult, rejoin, gameOver }
}
