# 🎵 TrackBack

TrackBack is a music-based game where players have to sort the songs currently being played by year of release.

## 1. Requirements

### 1.1. General

The game is implemented in python. 
Make sure you have `python3` (3.12 or higher) and `pip`  installed on your system. 
You can check by running on the command line:

```
python3 --version
pip --version
```

### 1.2. Using Spotify

- ✅ You need a Spotify Premium Account
- ✅ You must register the app in the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) 
   1. Log in and **create a new app**
   2. Specify a **redirect URI**:  e.g. `http://localhost:8888/callback`
   2. Go to setting and note down the following credentials:
      - `Client ID`
      - `Client secret`
   3. Spotify requires you to **add each player’s Spotify account** as an approved user:
      - Go to your app in the developer dashboard
      - Click **Edit Settings**
      - Add their Spotify Account details under **"User Management"**

### 1.3. Using Apple Music

- ✅ Playing music from Apple Music only works on machines running on macOS (Catalina (10.15)+).
- ✅ The "Music" app must be installed on the machine.

## 2. Installation

### 2.1. General

1. Clone the repository or download the code (`Download zip`).
2. On the top level of the created directory call `pip install .`

### 2.2. Using Spotify

- Inside the top-level directory edit the .env file and pass the information the found in the spotify developers section:

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=your-redirect-uri
```

- In the config.toml following setting is required:

```
music_provider = "spotify"
```

### 2.3. Using Apple Music

- In the config.toml following setting is required:

```
music_provider = "applemusic"
```

## 3. Run the game

### 3.1. Using Spotify

1. The spotify app must be open on a user's device. A user who has been registered for the app in the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) must be logged in.
2. A playlist to be used for the must be selected.
3. Run `track-back` to play the game.
4. When the game starts you will need to authenticate with the spotify credentials of the user mentioned under point 2.

### 3.2. Using Apple Music

1. The Music app must be running and a playlist to be used for the game must be selected.

2. Run `track-back` to play the game.

## 4. Development Setup - not necessary for execution

If you are developing or testing and need to use the source code directly:

- Run `make setup-venv` to create and activate a virtual environment. The python interpreter is located in `.venv/bin/python3`.

- Run `make install` to install the project in develop mode.

- Run `make test` to run the tests. ToDo: implement tests.