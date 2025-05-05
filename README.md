# 🎵 TrackBack

**TrackBack** is a music-based game where players must sort currently playing songs by their year of release.

You can play using your own playlists — it currently supports **Spotify** and **Apple Music**, and is built for easy extension to other music services.

The game consists of a **Python-based server** and a [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html) as frontend.

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

---

## 2. Connect to a music service

### 2.1 Spotify

#### 2.1.1 Requirements
- Spotify Premium account
- A registered app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   1. Log in and create a new app
   2. Set a **redirect URI**. The path must be `/spotify-callback` for the Spotify login flow in this app to work, e.g. `https://your-domain.com/spotify-callback`.
   3. Copy your **Client ID** and **Client Secret**
   4. Add authorized users under **Edit Settings > User Management**

#### 2.1.2 Setup

1. Copy `.env.example` to `.env`, and fill in your spotify credentials (see 2.1.).
2. Open the Spotify app and log in with a registered account (see 2.1.1).
3. Select a playlist to use in the game.

---

### 2.2 Apple Music

#### 2.2.1 Requirements
- macOS Catalina (10.15+)
- Music app installed and running

#### 2.2.2 Setup

- Open the Music app and select a playlist.

> Note: Apple Music integration uses AppleScript under the hood and only works on macOS.

---

## 3. Start the server

To start the game server run:

```bash
track-back-server
```

> Note: Call `track-back-server -h` to display help and information about optional arguments.

---

## 4. Play the game in the browser

Open the [Web UI](https://acc-aqt.github.io/track-back/web_ui/index.html) (or launch it locally by opening `web_ui/index.html`).

1. Enter the **Server URL** and a **username**
2. Click **Connect** to join
3. Click **Start Game** to begin once all players are connected

> Note: The server URL should look like `http://localhost:4200` or your network IP.

## 5. Development setup (not necessary to run the game)

For code development and testing:

```bash
make setup-venv   # Sets up .venv/ virtual environment
make install      # Installs in "editable" mode
make test         # Runs tests
```

---

## License

MIT License

