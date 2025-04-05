# 🎵 TrackBack

**TrackBack** is a music-based game where players need to sort currently playing songs by their year of release.

Trackback lets you play with your own playlists – currently supports Spotify & Apple Music, and is built to easily extend to other music services.

So far, user input is possible only via the command line.
A browser-based GUI is under development. 
-------

# 1 Installation

## 1.1 Requirements

The game is implemented in python. You need

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

## 2 Connecting with Spotify

### 2.1 Requirements
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

### 2.2 Setup

1.  Add your Spotify app credentials (see 2.1.) to the `.env` file in the root directory.

```env
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
SPOTIFY_REDIRECT_URI=your-redirect-uri
```

2.  In the `config.toml` set:

```toml
music_provider = "spotify"
```

### 2.3 Run the game

1. Ensure the Spotify app is open on a device and a registered user (see 2.1.) is logged in
2. Select a playlist that should be used during the game
3. Run the game:
```bash
track-back
```
4. When prompted, authenticate with the Spotify credentials of the registered user

-------

## 3 Connecting with Apple Music

### 3.1 Requirements
- Only supported on macOS Catalina (10.15+)
- The built-in `Music` app must be installed and running

### 3.2 Setup

- In the `config.toml` set:

```toml
music_provider = "applemusic"
```

### 3.3 Run the game

1. Open the Music app and select a playlist

2. Run the game:
```bash
track-back
```

Note: Apple Music control is only available on macOS and uses AppleScript under the hood.

-------

## 4 Development Setup - not necessary to run the game

If you are developing or testing and need to use the source code directly:

```bash
make setup-venv   # Sets up virtual environment (.venv/)
make install      # Installs in develop mode
make test         # Runs tests
```

-------

## 5 To-Dos

- Implement Web-based GUI
- Implement further music services (e.g. youtube, deezer, soundcloud)