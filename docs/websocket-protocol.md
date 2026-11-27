# TrackBack WebSocket protocol

The REST endpoints (`/create`, `/list-sessions`, `/join`, `/start`) are described in [`openapi.json`](openapi.json). Gameplay happens over one WebSocket per player, described here.

All frames are text frames that contain one JSON object. Every object has a `type` field.

## Wire names and glossary terms

Some wire names predate [`GLOSSARY.md`](../GLOSSARY.md). They stay as they are so that existing clients and servers keep working together, but they mean the glossary terms below.

| Wire name | Glossary term |
| --- | --- |
| `game_id` (path, HTTP bodies, Spotify login state) | Game Session Name |
| `username`, `user_name` | Username of a Player |
| `song_list` | Timeline |
| `your_turn` | Asks a Player for a Guess of the current Song |
| `next_player` (in `your_turn`) | The Player asked for the Guess |
| `user_disconnected` | A Player became a Disconnected Player |

## Endpoint

```
ws://<host>:<port>/ws/{game_id}/{username}
```

Use `wss://` when the server runs with SSL.

| Path parameter | Meaning |
| --- | --- |
| `game_id` | The Game Session Name used in `/create`. |
| `username` | The player's name. It must follow the name rule in the README (at most 20 characters). |

## Lifecycle

### Before the game starts (lobby)

1. The client calls `POST /join`. The server registers the name and broadcasts `player_joined` to everyone already connected.
2. The client opens the WebSocket. The server sends `welcome` and attaches the socket to the player.
3. The host calls `POST /start`. It fails with 409 if the game is already running or if any registered player has no open WebSocket. On success, every player receives `your_turn`.

A client may also open the WebSocket in the lobby without calling `POST /join` first. The server then registers the name silently: it sends `welcome` to that client, but nobody receives `player_joined`.

A player who disconnects in the lobby is removed from the session; everyone else receives `user_disconnected`. When the last player leaves the lobby, the session is deleted.

### Connecting to a running game (rejoin)

Opening the WebSocket is how a player gets back into a running game. A `POST /join` first is optional: on a running game it only checks that the name belongs to a player of the game and is not currently connected, and changes nothing.

When a player of the running game connects, they:

1. receive `welcome`;
2. are marked active again;
3. receive their own state:
   - if they still owe a guess for the current song: `your_turn` with their timeline, while everyone else receives `player_rejoined`;
   - if they already guessed the current song: no `your_turn`, but `player_rejoined` (which contains their timeline) goes to everyone, including themselves.

If the name is not a player of the game, or that player already has an open WebSocket, the server sends `error` and closes the socket with code 1008.

### Disconnecting from a running game

When a player's socket closes during a running game:

1. Everyone still connected receives `user_disconnected`.
2. The server stops waiting for that player's guess. If every player who is still connected has now guessed, the next song starts and every connected player receives `your_turn`. If nobody is connected, the round stays as it is for returning players.
3. If that was the last open socket, the session is kept for a grace period of 10 minutes so that players can rejoin. A session that is still empty after the grace period is removed the next time a session is listed, created or joined.

### After the game is over

The game ends when a player's timeline reaches the Target Song Count. Every player receives `game_over`; nobody receives another `your_turn`. The sockets stay open. A client that connects to a finished game receives `game_over` and the socket is closed. A finished game is removed when its last player disconnects.

Until then the finished game is deliberately not joinable: `GET /list-sessions` leaves it out, and `POST /join` on it returns 409 with `Game session <game_id> is already over.`

### Rejected connections

| Situation | Server behaviour |
| --- | --- |
| `username` breaks the name rule | Socket closed with code 1008, reason `Invalid user name.`, no message. |
| `game_id` doesn't exist | Socket closed, no message. |
| Not a player of a running game, or already connected | `error`, then socket closed with code 1008. |
| Game is over | `game_over`, then socket closed. |

## Shared objects

**Song**

```json
{"title": "Yesterday", "artist": "The Beatles", "release_year": 1965, "album_cover_url": ""}
```

`album_cover_url` is an empty string when the music service has no cover. Otherwise it is either a full URL (Spotify) or a path on the game server starting with `/`, such as `/covers/<id>` (Apple Music), which the client resolves against the server URL.

**Timeline**: a list of Songs ordered by release year, oldest first. Sent as `song_list`.

**Player**: `{"name": "<username>", "song_list": [<Song>, ...]}`.

## Server to client messages

### `welcome`

Sent to a player right after their WebSocket is accepted, in the lobby and when rejoining.

| Field | Type | Meaning |
| --- | --- | --- |
| `message` | string | `Welcome <username>, you're connected.` |

### `your_turn`

Asks a player to place the song that is now playing. Sent to every active player when the game starts and when a new round starts (after the last guess of a round, or after the last owed guesser disconnects), and to a rejoining player who still owes a guess.

| Field | Type | Meaning |
| --- | --- | --- |
| `message` | string | `Place the new Song in your Timeline!` on start and rejoin, `New round! Make your guess!` on a new round. |
| `next_player` | string | The name of the receiving player. |
| `song_list` | Timeline | The receiving player's timeline. |

### `guess_result`

Sent only to the player who sent a valid `guess`.

| Field | Type | Meaning |
| --- | --- | --- |
| `player` | string | The guessing player. |
| `result` | string | `correct` or `wrong`. A correct song is added to the timeline. |
| `message` | string | Names the song, e.g. `Song was 'Yesterday' by The Beatles (1965).` |
| `last_song` | Song | The song that was guessed. |
| `last_index` | string | The guessed `index`, as a string. |
| `song_list` | Timeline | The player's timeline after the guess. |
| `other_players` | list of Player | Every other player with their timeline. |
| `game_over` | boolean | `true` if this guess won the game. |
| `winner` | string | The winner's name, or `""` while the game continues. |

### `other_player_guess`

Sent to every other connected player after a player's `guess_result`.

| Field | Type | Meaning |
| --- | --- | --- |
| `player` | string | The guessing player. |
| `result` | string | `correct` or `wrong`. |
| `message` | string | `<player> made a guess. Guess was <result>.` |

### `player_joined`

Broadcast to every connected player when someone calls `POST /join` on a game that hasn't started.

| Field | Type | Meaning |
| --- | --- | --- |
| `user_name` | string | The new player. |
| `message` | string | `<user_name> joined the game! There are now <n> players: <names>.` |

### `player_rejoined`

Sent when a player reconnects to a running game. See [Connecting to a running game](#connecting-to-a-running-game-rejoin) for who receives it.

| Field | Type | Meaning |
| --- | --- | --- |
| `user_name` | string | The returning player. |
| `song_list` | Timeline | The returning player's timeline. |
| `message` | string | `<user_name> re-joined the game! There are now <n> players: <names>.` |

### `user_disconnected`

Broadcast to every connected player when a player's socket closes.

| Field | Type | Meaning |
| --- | --- | --- |
| `message` | string | `<username> disconnected. <username> can try to re-join the game.` |

### `game_over`

Broadcast to every connected player after the winning guess, and sent to a client that connects to a finished game.

| Field | Type | Meaning |
| --- | --- | --- |
| `winner` | string | The winner's name. |
| `message` | string | `<winner> has won the game!` |

### `error`

Sent to one player when their connection or message is rejected. The socket stays open unless the connection itself was rejected (see [Rejected connections](#rejected-connections)).

| Field | Type | Meaning |
| --- | --- | --- |
| `message` | string | What went wrong. |

Messages the server sends:

- `Invalid JSON.` / `Expected an object.` / `Unknown message type.`: the frame couldn't be dispatched.
- `Guess index must be an integer.`: `guess` without an integer `index`.
- `Game not running.`: `guess` before the game started or after it ended.
- `<username> has already guessed this song.`: a second `guess` in the same round.
- `Invalid position <index>.`: `index` is outside the timeline.
- A music-service error text, if the Round's Song couldn't be read when the Round started and still can't be read on a `guess`. The `guess` isn't counted and can be sent again.
- `Player '<username>' is not a player in game session <game_id>. Only one of the following players can rejoin: <names>.` / `Player '<username>' is already connected to game session <game_id>. Only one of the following players can rejoin: <names>.`: rejected rejoin. `POST /join` on a running game returns the same text as a 409.

## Client to server messages

### `guess`

Places the current song in the player's timeline.

| Field | Type | Meaning |
| --- | --- | --- |
| `index` | integer | The position to insert the song at, from `0` (before the oldest song) to the length of the timeline (after the newest song). |

```json
{"type": "guess", "index": 0}
```

Each player can guess once per round. The round ends when every active player has guessed; then every active player receives `your_turn` for the next song.

### `ping`

Keepalive. The server sends no reply. The Web UI sends one every 10 seconds.

```json
{"type": "ping"}
```
