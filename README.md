# 🎵 TrackBack

TrackBack is a music-based game where players have to sort the songs currently being played by year of release.

## Requirements

### General

The game is implemented in python. 
Make sure you have `pip` and `python3` (3.12 or higher) installed on your system. 
You can check by running on the command line:

```
python3 --version
pip --version
```

### Using Spotify

- ✅ You need a Spotify Premium Account
- ✅ Access to the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) 
   1. Log in and **create a new app**
   2. Specify a **redirect URI**:  e.g. `http://localhost:8888/callback`
   2. Go to setting and note down the following credentials:
      - `Client ID`
      - `Client secret`
   3. Spotify requires you to **add each player’s Spotify account** as an approved user:

      - Go to your app in the developer dashboard
      - Click **Edit Settings**
      - Add their Spotify Account details under **"User Management"**

### Using Apple Music

- ✅ Playing music from Apple Music only works on machines running on macOS (Catalina (10.15)+).
- ✅ The "Music" app must be installed on the machine.

## Installation

1. Clone the repository or download the code ("Download zip").
2. On the top level of the created directory call 'pip install .'


## Execution

### Using Spotify
Inside the track-back directory create a .env file containing the information found in the spotify developers section:

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=your-redirect-uri
```

In the config.toml following setting is required:

```
music_provider = "spotify"
```

Call `track-back` to play the game.

You will need to authenticate with a spotify account that has been registered in the spotify for developers section.

### Using AppleMusic

In the config.toml following setting is required:

```
music_provider = "applemusic"
```

The Music app must be running and a playlist to be used for the game must be selected.

Call `track-back` to play the game.

## Development Setup (if needed)

If you are developing or testing and need to use the source code directly:

- Run `make setup-venv` to create and activate a virtual environment. The python interpreter is located in `.venv/bin/python3`.

- Run `make install` to install the project in develop mode.

- Run `make test` to run the tests. ToDo: implement tests.