// Choices remembered in the browser between visits.

export const USERNAME_KEY = 'trackback.username'
export const TARGET_SONG_COUNT_KEY = 'trackback.targetSongCount'
export const MUSIC_SERVICE_KEY = 'trackback.musicService'

export const loadStored = key => {
  try {
    return localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

export const store = (key, value) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Storage can be unavailable (private mode); the value is then just not remembered.
  }
}
