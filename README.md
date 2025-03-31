# track-back

## Description

A game where players sort songs played by release date.

## Prerequisites
Make sure you have `pip` and `python3` installed on your system. You can check by running on the command line:

```
python3 --version
pip --version
```

- ToDo: Docu for Spotify for Developers

## Installation

Clone the repository and install the package using pip:

```
git clone git@github.com:acc-aqt/track-back.git
cd track-back
pip install .
```

Inside the track-back directory create a .env file containing the information found in the spotify developers section:

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=your-redirect-uri
```

## Execution

Call `run-track-back` to run the server.

## Development Setup (if needed)

If you are developing or testing and need to use the source code directly:

- Run `make setup-venv` to create and activate a virtual environment. The python interpreter is located in `.venv/bin/python3`.

- Run `make install` to install the project in develop mode.

- Run `make test` to run the tests.