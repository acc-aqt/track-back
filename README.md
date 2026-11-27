<p align="center">
  <img src="web_ui/assets/logo.svg" alt="TrackBack logo" width="96" />
</p>

# TrackBack

[![Tests](https://github.com/acc-aqt/track-back/actions/workflows/test.yml/badge.svg)](https://github.com/acc-aqt/track-back/actions/workflows/test.yml)

**TrackBack** is a music-based game where players must sort currently playing songs by their year of release.

Watch the demo video [here](https://youtube.com/shorts/5E3Vtzxa9SE?feature=shared).

You can play using your own playlists — it currently supports **Spotify** and **Apple Music**, and is built for easy extension to other music services.

The game consists of a **Python-based server** and a [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html) as frontend.

> **Intended use / security:** TrackBack is a party game for friends on a local network. There are no accounts or authentication: anyone who can reach the server can create, list and join game sessions. Don't expose the server to the public internet unless you're fine with that.

---

## 1. Installation

### 1.1 Requirements

To run the game server, you need:

- `Python 3.11` or higher
- `pip`

You can check your installed versions as follows:

```bash
python3 --version
pip --version
```

### 1.2 Install

1. Clone the repository:

```bash
git clone https://github.com/acc-aqt/track-back.git
cd track-back
```

(Or download the ZIP.)

2. Install dependencies:

```bash
pip install .
```

### 1.3 Configure

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

`.env` holds your Spotify credentials (see 2.1.2) and, optionally, the SSL paths for HTTPS (see 3). Leave the values empty for features you don't use.

| Variable | Purpose |
| --- | --- |
| `PORT` | Port the server listens on (default `4200`). `track-back-server --port <port>` takes precedence. |
| `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI` | Spotify app credentials (see 2.1.2). |
| `SSL_KEYFILE`, `SSL_CERTFILE` | Paths to the key and certificate for HTTPS (see 3). |

---

## 2. Connect to a music service

### 2.1 Spotify

#### 2.1.1 Requirements
- Spotify Premium account (Spotify only allows playback control for Premium accounts)
- A registered app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   1. Log in and create a new app
   2. Set a **redirect URI**. The path must be `/spotify-callback` for the Spotify login flow in this app to work, e.g. `https://your-domain.com/spotify-callback`.
   3. Copy your **Client ID** and **Client Secret**
   4. Add authorized users under **Edit Settings > User Management**

#### 2.1.2 Setup

1. Fill in `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET` and `SPOTIPY_REDIRECT_URI` in your `.env` (see 1.3) with the values from 2.1.1.
2. Open the Spotify app and log in with a registered account (see 2.1.1).
3. Select a playlist to use in the game.

---

### 2.2 Apple Music

#### 2.2.1 Requirements
- macOS Catalina (10.15+)
- Music app installed and running **on the same Mac as the game server**

#### 2.2.2 Setup

1. Open the Music app and select a playlist. Shuffle works well.
2. Start the server (see 3) and create a game with **Apple Music**.
3. On the first game, macOS asks whether your terminal may control **Music** and **System Events**. Allow both. You can change this later under **System Settings > Privacy & Security > Automation**.

How it works: the server talks to the Music app via AppleScript. It starts playback, reads the title, artist and **Year** field of the current track, and skips to the next track after each round.

> Notes:
> - The release year comes from the track's **Year** field in your library. Tracks without a year count as year 0, so check your playlist's metadata.
> - Apple Music doesn't provide album covers to the game, so placeholder covers are shown.

---

## 3. Start the server

To start the game server run:

```bash
track-back-server
```

> Note: Call `track-back-server -h` to display help and information about optional arguments.

#### Run with HTTPS (Optional)

To serve the game securely via HTTPS, you can run the server with an SSL certificate.

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

Step 2: Set `SSL_KEYFILE` and `SSL_CERTFILE` in your `.env` (see 1.3) to the paths of `key.pem` and `cert.pem`.

If both variables are set, the server will automatically start with SSL enabled.

---

## 4. Play the game in the browser

Open the [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html), or open `web_ui/index.html` locally. (The `index.html` in the repo root only redirects the GitHub Pages root to the Web UI.)

If the page doesn't come with a preconfigured server, it first shows a **Server** field. Enter your server's address, e.g. `http://localhost:4200` or `http://<your-lan-ip>:4200`.

Every player enters a **Username** of up to 20 characters. Usernames and **Game Session Names** (up to 40 characters) follow the same rule: one or more words separated by single spaces, where each word uses only letters and digits from any script (Unicode categories L and N, e.g. `Jörg`, `李雷`, `٣٤`), `_` and `-`. No leading, trailing or double spaces.

### 4.1 Host a game

1. Click **Configure new Game Session**.
2. In **Game Setup**, choose the music service, a **Game Session Name** (defaults to `Game-by-<username>`) and the **Target Song Count** (at least 1): the first player whose timeline reaches it wins.
3. Click **Create new Game Session**.
   - **Spotify:** a Spotify login opens in a new tab. Log in, close the tab, and click **Join the new game session** in the game.
   - **Apple Music:** the session is created and you join it directly.
4. Wait until everyone has joined, then click **All players connected? Start!**

### 4.2 Join a game

1. Click **Join a Game**.
2. Pick the session from the list and click **Join Selected Session**.
3. Wait for the host to start the game.

### 4.3 Play

- Each round, a song plays and a new card appears above your timeline. Drag it to the position where it belongs by release year.
- Correct guesses stay in your timeline. A wrong guess is shown briefly at the position you chose, then removed.
- The first player to reach the target song count wins.
- If you lose your connection, join the same session again with the same username to continue.

> The **Mock Music Service** option (a fixed list of songs, no real playback) is only shown when the Web UI runs on `localhost`. It's meant for development.

## 5. Development setup (not necessary to run the game)

For code development and testing:

```bash
make create-venv           # Creates .venv/ and installs the package with test and lint extras
source .venv/bin/activate  # Activates the virtual environment in your shell
make test                  # Runs the tests with coverage
make lint                  # Checks ruff lint, ruff format and mypy on src/ and tests/ (same as CI)
make format                # Applies ruff fixes and formatting
make run                   # Starts the game server
make openapi               # Regenerates docs/openapi.json
```

The HTTP API is described in [docs/openapi.json](docs/openapi.json), the WebSocket messages in [docs/websocket-protocol.md](docs/websocket-protocol.md).

---

## License

MIT License
