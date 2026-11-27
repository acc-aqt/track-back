// The name rules for Usernames and Game Session Names.

const NAME_PATTERN = /^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u
export const USERNAME_MAX_LENGTH = 20
export const SESSION_NAME_MAX_LENGTH = 40

export const isValidUsername = name =>
  name.length <= USERNAME_MAX_LENGTH && NAME_PATTERN.test(name)

export const isValidSessionName = id =>
  id.length <= SESSION_NAME_MAX_LENGTH && NAME_PATTERN.test(id)
