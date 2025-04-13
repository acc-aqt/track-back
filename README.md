# 🎵 TrackBack

**TrackBack** is a music-based game where players need to sort currently playing songs by their year of release.

Trackback lets you play with your own playlists – it currently supports Spotify & Apple Music, and is built to easily extend to other music services.

The game consists of a game server (written in python). As frontend there is either a command line interface (written in python) or a web ui that can be used in any browser.

-------

# 1 Installation

## 1.1 Requirements

The game server is implemented in python. To run the server you need

- `Python 3.12` or higher
- `pip` for package management

You can check your installed versions as follows:

```bash
python3 --version
pip --version
```

## 1.2 Run installation

1. Clone this repository:
```bash
git clone https://github.com/acc-aqt/track-back.git
cd track-back
```
(Alternatively you can download the code using `Download zip`.)

2. Install dependencies:
```bash
pip install .
```

-------

# 2 Connecting with music services
## 2.1 Spotify

### 2.1.1 Requirements
- A Spotify Premium account is required
- The game must be registered in the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) 
   1. Log in and create a new app
   2. Specify a redirect URI:  e.g. `http://localhost:8888/callback`
   2. Go to `Edit Settings` and note down the following credentials:
      - `Client ID`
      - `Client secret`
   3. Add the users
      - Go to `Edit Settings`
      - Under `User Management`, add the Spotify accounts of users who should be allowed to play

### 2.1.2 Setup

1.  Rename the `.env.example` file in the root directory to `.env` and add your spotify credentials (see 2.1.).

2.  In the `config.toml` set:

```toml
music_service = "spotify"
```

3. Ensure the Spotify app is open on a device and a registered user (see 2.1.1) is logged in
4. Select a playlist that should be used during the game


## 2.2 Apple Music

### 2.2.1 Requirements
- Only supported on macOS Catalina (10.15+)
- The built-in `Music` app must be installed and running

### 2.2.2 Setup

- In the `config.toml` set:

```toml
music_service = "applemusic"
```
- Open the Music app and select a playlist

- Note: Apple Music control is only available on macOS and uses AppleScript under the hood.

-------

# 3 Start the game server

To start the game server run
```bash
track-back-server
```

-------

# 4 Play the game

You can either play in the browser or via command line

# 4.1 Web UI

ToDo!

# 4.2 Command line

ToDo!


## 5 Development Setup - not necessary to run the game

If you are developing or testing and need to use the source code directly:

```bash
make setup-venv   # Sets up virtual environment (.venv/)
make install      # Installs in develop mode
make test         # Runs tests
```

-------

## 5 To-Dos

- Implement further music services (e.g. youtube, deezer, soundcloud)