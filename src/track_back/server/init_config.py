"""Interactively create the per-user config file (``track-back-server init``)."""

from track_back.server import config

DEFAULT_PORT = "4200"


def ask(prompt: str, default: str = "") -> str:
    """Prompt for a value, returning ``default`` when the answer is empty."""
    suffix = f" [{default}]" if default else ""
    return input(f"{prompt}{suffix}: ").strip() or default


def confirm(prompt: str) -> bool:
    """Ask a yes/no question that defaults to no."""
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def run() -> None:
    """Ask the host for config values and write them to the per-user config file."""
    path = config.user_config_path()
    if path.exists() and not confirm(f"{path} already exists. Overwrite?"):
        print(f"Left {path} unchanged.")
        return

    port = ask("Port", DEFAULT_PORT)
    while not port.isdigit():
        print("Port must be a number.")
        port = ask("Port", DEFAULT_PORT)
    client_id = ""
    client_secret = ""
    redirect_uri = ""
    if confirm("Set up Spotify?"):
        client_id = ask("Spotify client ID")
        client_secret = ask("Spotify client secret")
        redirect_uri = ask(
            "Spotify redirect URI", f"http://127.0.0.1:{port}/spotify-callback"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"PORT={port}\n"
        "SSL_KEYFILE=\n"
        "SSL_CERTFILE=\n"
        f"SPOTIPY_CLIENT_ID={client_id}\n"
        f"SPOTIPY_CLIENT_SECRET={client_secret}\n"
        f"SPOTIPY_REDIRECT_URI={redirect_uri}\n"
    )
    print(f"Wrote config to {path}")
