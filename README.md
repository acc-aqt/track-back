<p align="center">
  <img src="web_ui/assets/logo.svg" alt="TrackBack logo" width="96" />
</p>

# TrackBack

[![Tests](https://github.com/acc-aqt/track-back/actions/workflows/test.yml/badge.svg)](https://github.com/acc-aqt/track-back/actions/workflows/test.yml)

**TrackBack** is a music-based game where players must sort currently playing songs by their year of release.

Watch the demo video [here](https://youtube.com/shorts/5E3Vtzxa9SE?feature=shared).

You can play using your own playlists — it currently supports **Spotify** and **Apple Music**, and is built for easy extension to other music services.

The game consists of a **Python-based server** and a [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html) as frontend.

---

## 1. Installation

> **Intended use / security:** TrackBack is a party game for friends on a local network. There are no accounts or authentication: anyone who can reach the server can create, list and join game sessions. Don't expose the server to the public internet unless you're fine with that.

### 1.1 Requirements

- `Python 3.11` or higher
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) or [`pipx`](https://pipx.pypa.io/stable/installation/)

### 1.2 Install and start

1. Install TrackBack:

```bash
uv tool install track-back
```

(Or `pipx install track-back`.)

2. Create your config. `init` asks which Music Service you use (`applemusic` or `spotify`, with your platform's default suggested), the port and, only if you choose `spotify`, your Spotify credentials (see 3 and 3.1):

```bash
track-back-server init
```

3. Start the server:

```bash
track-back-server
```

4. The server opens the game in your default browser. If it can't, or you started it with `--no-browser` (e.g. on a headless machine), open the URL the server prints, e.g. `Open http://localhost:4200 on this machine, or http://192.168.1.20:4200 on other devices.` The other players open the second one on their own devices (see 4).

> Note: Call `track-back-server -h` to display help and information about optional arguments, and `track-back-server --version` to show the installed version.

### 1.3 Upgrade and uninstall

```bash
uv tool upgrade track-back     # or: pipx upgrade track-back
uv tool uninstall track-back   # or: pipx uninstall track-back
```

Uninstalling leaves your config file in place (see 2.2). Delete it by hand if you don't need it anymore.

---

## 2. Configuration

### 2.1 Where config comes from

The server reads its settings from these sources, highest precedence first. A value set in an earlier source is never overridden by a later one:

1. Environment variables
2. The file passed with `track-back-server --env-file <path>`
3. `.env` in the current working directory (or the nearest parent directory that has one)
4. The per-user config file written by `track-back-server init`

`track-back-server --port <port>` and `--music-service <service>` take precedence over all of them.

### 2.2 Per-user config file

| OS | Location |
| --- | --- |
| macOS | `~/Library/Application Support/track-back/.env` |
| Linux | `~/.config/track-back/.env` (or `$XDG_CONFIG_HOME/track-back/.env`) |
| Windows | `%LOCALAPPDATA%\track-back\.env` |

Re-run `track-back-server init` to replace it (it asks before overwriting), or edit it directly. To write a dotenv file of your own, start from [.env.example](.env.example).

### 2.3 Variables

Leave the values empty for features you don't use.

| Variable | Purpose |
| --- | --- |
| `PORT` | Port the server listens on (default `4200`). |
| `MUSIC_SERVICE` | Music Service the server uses: `applemusic`, `spotify` or `mock` (default `applemusic` on macOS, `spotify` elsewhere; see 3). |
| `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI` | Spotify app credentials (see 3.1). |
| `SSL_KEYFILE`, `SSL_CERTFILE` | Paths to the key and certificate for HTTPS (see 5). |

---

## 3. Connect to a music service

The Server Operator chooses the Music Service when starting the server. Every Game Session uses it, unless the Host switches to another one that's available on the server.

- **Default:** Apple Music on macOS, Spotify on Windows and Linux.
- **Switch:** re-run `track-back-server init`, set `MUSIC_SERVICE` in your config (see 2.3), or pass `track-back-server --music-service spotify|applemusic` for one start. The option takes precedence over `MUSIC_SERVICE`.
- **Available services:** Apple Music on macOS, Spotify when `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET` and `SPOTIPY_REDIRECT_URI` are all set, and the Mock Music Service only when the server was started with it.
- **Per Game Session:** the hosting **Options** show "Music: <service> · change" (see 4.1). "change" lists the available services and only affects that Game Session; it's hidden when only one service is available.

If the chosen Music Service can't work on this machine, the server refuses to start and prints how to fix it: run `track-back-server init` to add Spotify credentials, or use `--music-service spotify` instead of Apple Music on a machine that isn't a Mac. An unknown `MUSIC_SERVICE` value stops the server with a list of the valid values.

### 3.1 Spotify

#### 3.1.1 Requirements
- Spotify Premium account (Spotify only allows playback control for Premium accounts)
- A registered app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   1. Log in and create a new app
   2. Set a **redirect URI**. The path must be `/spotify-callback`. We recommend the loopback address `http://127.0.0.1:4200/spotify-callback` (with your port; Spotify doesn't accept `localhost`).
   3. Copy your **Client ID** and **Client Secret**
   4. Add authorized users under **Edit Settings > User Management**

#### 3.1.2 Setup

1. Run `track-back-server init`, answer `spotify` to **Music service** and enter the Client ID, Client Secret and redirect URI from 3.1.1. The suggested default redirect URI is the loopback one for your port.
2. Open the Spotify app and log in with a registered account (see 3.1.1).
3. Select a playlist to use in the game.

> With the loopback redirect URI, the host must create Spotify games in a browser **on the server machine**, because Spotify sends the browser back to `127.0.0.1` after login. To log into Spotify from another device, the redirect URI has to point at the server's LAN address, and Spotify only accepts that over HTTPS: set up HTTPS (see 5) and use e.g. `https://192.168.1.20:4200/spotify-callback` in both the dashboard and your config.

---

### 3.2 Apple Music

#### 3.2.1 Requirements
- macOS Catalina (10.15+)
- Music app installed and running **on the same Mac as the game server**

#### 3.2.2 Setup

1. Open the Music app and select a playlist. Shuffle works well.
2. Start the server (see 1.2) and host a game with **Apple Music** (see 4.1).
3. On the first game, macOS asks whether your terminal may control **Music** and **System Events**. Allow both. You can change this later under **System Settings > Privacy & Security > Automation**.

How it works: the server talks to the Music app via AppleScript. It starts playback, reads the title, artist, **Year** field and album artwork of the current track, and skips to the next track after each round.

> Notes:
> - The release year comes from the track's **Year** field in your library. Tracks without a year count as year 0, so check your playlist's metadata.
> - Album covers are shrunk to 300 px with the built-in `sips` tool and served by the game server. Tracks without artwork show a placeholder cover.

---

## 4. Play the game in the browser

The server serves the Web UI itself: open the URL it prints at start-up (e.g. `http://localhost:4200/` on the server machine, `http://<your-lan-ip>:4200/` on other devices) and the page already talks to that server.

Alternatively, open the public [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html) on GitHub Pages. It's published from `src/track_back/web_ui/` by the Pages workflow on every push to `main`. (The `index.html` in the repo root only redirects the GitHub Pages root to the Web UI.)

If the page doesn't come with a preconfigured server, it first shows a **Server** field. Enter your server's address, e.g. `http://localhost:4200` or `http://<your-lan-ip>:4200`.

Every player enters a **Username** of up to 20 characters. Usernames and **Game Session Names** (up to 40 characters) follow the same rule: one or more words separated by single spaces, where each word uses only letters and digits from any script (Unicode categories L and N, e.g. `Jörg`, `李雷`, `٣٤`), `_` and `-`. No leading, trailing or double spaces.

### 4.1 Host a game

1. Enter your **Username** and click **Host a game**. This creates a Game Session right away with these defaults:
   - **Game Session Name:** `Game-by-<username>`
   - **Target Song Count:** 10, or the one you used last time in this browser. The first player whose timeline reaches it wins.
   - **Music Service:** the one you used last time if the server still offers it, otherwise the server's default (see 3).
2. To change any of them first, click **Options** below the button. It shows the **Game Session Name**, the **Target Song Count** (at least 1) and a line **Music: <service> · change**. **change** lists the Music Services available on this server and is hidden when there's only one. Then click **Host a game**.
   - If the Game Session Name is already taken, **Options** opens with the error so you can pick another name.
   - The Target Song Count and Music Service are remembered in this browser for the next time you host.
3. What happens next depends on the Music Service:
   - **Spotify:** the Spotify login opens in the same tab. After you log in, you're taken back to the game and join your new Game Session automatically, with your Username kept (also when you opened the game on `localhost` and Spotify returns you to `127.0.0.1`). A failed login shows an error page.
   - **Apple Music** (or the Mock Music Service): you join your new Game Session directly.
4. In the **Lobby**, a QR code shows the link to your Game Session (**Show bigger** enlarges it). Friends scan it and only need to enter their Username. It disappears once the game starts.
5. Wait until everyone has joined, then click **All players connected? Start!**

> Against an older server without the Music Service choice, **Options** shows the full Spotify / Apple Music dropdown instead of the **Music** line, and the QR code is hidden.

### 4.2 Join a game

1. Scan the QR code in the Host's Lobby, or open the game and click **Join a Game**.
   - When exactly one Game Session is open, you join it directly.
   - Otherwise, pick the session from the list and click **Join Selected Session**.
2. Wait for the Host to start the Game Session.

### 4.3 Play

- Each round, a song plays and a new card appears above your timeline. Drag it to the position where it belongs by release year.
- Correct guesses stay in your timeline. A wrong guess is shown briefly at the position you chose, then removed.
- The first player to reach the target song count wins.
- If you lose your connection, join the same session again with the same username to continue.

> The **Mock Music Service** (a fixed list of songs, no real playback) is meant for development. It's only available when the server was started with `--music-service mock`, as `make run` does.

---

## 5. Advanced: HTTPS

To serve the game via HTTPS, run the server with an SSL certificate. You need this to log into Spotify from a device other than the server machine (see 3.1.2).

Step 1: Generate a self-signed certificate

You can use OpenSSL to create a key and certificate:

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365
```

This will generate two files:
- key.pem: Your private key
- cert.pem: Your public certificate

> Note: Self-signed certificates will show browser warnings unless manually trusted. For production, use certificates from a trusted CA like Let’s Encrypt.

Step 2: Set `SSL_KEYFILE` and `SSL_CERTFILE` in your config (see 2) to the absolute paths of `key.pem` and `cert.pem`.

If both variables are set, the server will automatically start with SSL enabled, and the URLs it prints start with `https://`.

---

## 6. Development setup (not necessary to run the game)

To run the server from a checkout, clone the repository and install it:

```bash
git clone https://github.com/acc-aqt/track-back.git
cd track-back
pip install .
```

For code development and testing:

```bash
make create-venv           # Creates .venv/ and installs the package with test and lint extras
source .venv/bin/activate  # Activates the virtual environment in your shell
make test                  # Runs the tests with coverage
make lint                  # Checks ruff lint, ruff format and mypy on src/, tests/ and scripts/ (same as CI)
make format                # Applies ruff fixes and formatting
make run                   # Starts the game server with the Mock Music Service
make openapi               # Regenerates docs/openapi.json
```

The HTTP API is described in [docs/openapi.json](docs/openapi.json), the WebSocket messages in [docs/websocket-protocol.md](docs/websocket-protocol.md).

Releases to PyPI and the one-time Trusted Publisher setup are described in [docs/releasing.md](docs/releasing.md).

---

## License

MIT License
