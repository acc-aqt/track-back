// The name rules for Usernames and Game Session Names. The server hands them
// out in server_config.js; these are the values for a server that doesn't.
const FALLBACK_RULES = {
  NAME_PATTERN: '^[\\p{L}\\p{N}_-]+( [\\p{L}\\p{N}_-]+)*$',
  USERNAME_MAX_LENGTH: 20,
  SESSION_NAME_MAX_LENGTH: 40
}

const rule = key => window.TRACK_BACK_CONFIG?.[key] ?? FALLBACK_RULES[key]

const matchesNamePattern = name =>
  new RegExp(rule('NAME_PATTERN'), 'u').test(name)

// Counts characters like the server does, not UTF-16 code units.
const characterCount = name => [...name].length

export const usernameMaxLength = () => rule('USERNAME_MAX_LENGTH')

export const sessionNameMaxLength = () => rule('SESSION_NAME_MAX_LENGTH')

export const isValidUsername = name =>
  characterCount(name) <= usernameMaxLength() && matchesNamePattern(name)

export const isValidSessionName = id =>
  characterCount(id) <= sessionNameMaxLength() && matchesNamePattern(id)
