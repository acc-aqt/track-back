# 🎵 TrackBack

**TrackBack** is a music-based game where players need to sort currently playing songs by their year of release.

---

## 1. Requirements

### 1.1. General

The game is implemented in python. You need

- `Python 3.12` or higher
- `pip` for package management

You can check your installed versions as follows:

```bash
python3 --version
pip --version
```

### 1.2. Spotify

- ✅ A Spotify Premium account is required
- ✅ A registered app in the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) 
   1. Log in and create a new app
   2. Specify a **redirect URI**:  e.g. `http://localhost:8888/callback`
   2. Go to `Edit Settings` and note down the following credentials:
      - `Client ID`
      - `Client secret`
   3. Add the users
      - Go to `Edit Settings`
      - Under `User Management`, add the Spotify accounts of users who should be allowed to play

### 1.3. Apple Music

- ✅ Only supported on macOS Catalina (10.15+)
- ✅ The built-in Music app must be installed and running

## 2. Installation

### 2.1. General

1. Clone this repository:
```bash
git clone git@github.com:acc-aqt/track-back.git
cd track-back
```
(Alternatively you can download the code using `Download zip`.)

2. Install dependencies:
```bash
pip install .
```

### 2.2. Spotify Setup

1.  Add your Spotify app credentials to the `.env` file in the root directory.

```env
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=your-redirect-uri
```

2.  In the `config.toml` set:

```toml
music_provider = "spotify"
```

### 2.3. Apple Music Setup

- In the `config.toml` set:

```toml
music_provider = "applemusic"
```

## 3. Running the game

### 3.1. Using Spotify

1. Ensure the Spotify app is open on a device logged in with a registered user’s account
2. Select a playlist that should be used during the game
3. Run the game:
```bash
track-back
```
4. When prompted, authenticate with the Spotify credentials of the registered user

### 3.2. Using Apple Music

1. Open the Music app and select a playlist

2. Run the game:
```bash
track-back
```

Note: Apple Music control is only available on macOS and uses AppleScript under the hood.

## 4. Development Setup - not necessary for execution

If you are developing or testing and need to use the source code directly:

```bash
make setup-venv   # Sets up virtual environment (.venv/)
make install      # Installs in develop mode
make test         # Runs tests
```

## 📌 To-Do

- Add unit tests
- Implement Web-based GUI
- Implement further music services (e.g. youtube, deezer, soundcloud)