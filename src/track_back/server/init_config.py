"""Interactively create the per-user config file (``track-back-server init``)."""

from track_back.music_service.selection import MusicServiceType, default_music_service
from track_back.server import config

INIT_MUSIC_SERVICES = (MusicServiceType.APPLE_MUSIC, MusicServiceType.SPOTIFY)


def ask(prompt: str, default: str = "") -> str:
    """Prompt for a value, returning ``default`` when the answer is empty."""
    suffix = f" [{default}]" if default else ""
    return input(f"{prompt}{suffix}: ").strip() or default


def confirm(prompt: str) -> bool:
    """Ask a yes/no question that defaults to no."""
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def ask_music_service() -> MusicServiceType:
    """Ask which Music Service the server uses until the answer is valid."""
    choices = "/".join(INIT_MUSIC_SERVICES)
    while True:
        answer = ask(f"Music service [{choices}]", default_music_service())
        if answer in INIT_MUSIC_SERVICES:
            return MusicServiceType(answer)
        print(f"Music service must be one of: {', '.join(INIT_MUSIC_SERVICES)}.")


def run() -> None:
    """Ask the host for config values and write them to the per-user config file."""
    path = config.user_config_path()
    if path.exists() and not confirm(f"{path} already exists. Overwrite?"):
        print(f"Left {path} unchanged.")
        return

    music_service = ask_music_service()
    port = ask("Port", str(config.DEFAULT_PORT))
    while not port.isdigit():
        print("Port must be a number.")
        port = ask("Port", str(config.DEFAULT_PORT))
    client_id = ""
    client_secret = ""
    redirect_uri = ""
    if music_service == MusicServiceType.SPOTIFY:
        client_id = ask("Spotify client ID")
        client_secret = ask("Spotify client secret")
        redirect_uri = ask(
            "Spotify redirect URI", f"http://127.0.0.1:{port}/spotify-callback"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"PORT={port}\n"
        f"MUSIC_SERVICE={music_service}\n"
        "SSL_KEYFILE=\n"
        "SSL_CERTFILE=\n"
        f"SPOTIPY_CLIENT_ID={client_id}\n"
        f"SPOTIPY_CLIENT_SECRET={client_secret}\n"
        f"SPOTIPY_REDIRECT_URI={redirect_uri}\n"
    )
    print(f"Wrote config to {path}")
