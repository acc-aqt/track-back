"""Entry point to start the track-back server."""

import tomllib
from pathlib import Path

from dotenv import load_dotenv

from game.track_back_game import TrackBackGame
from game.user import get_users
from music_service.factory import MusicServiceFactory


def load_user_config(config_path: str = "config.toml") -> dict[str, str]:
    """Load user configuration from a TOML file."""
    with Path(config_path).open("rb") as f:
        return tomllib.load(f)


def main() -> None:
    """Execute the entry point to the game."""
    load_dotenv()  # load credentials from .env file

    config = load_user_config()

    provider = config.get("music_provider")
    music_provider = MusicServiceFactory.create_music_provider(provider)
    music_provider.start_playback()

    users = get_users()

    target_song_count = config.get("target_song_count")

    game = TrackBackGame(
        target_song_count=target_song_count,
        music_provider=music_provider,
        users=users,
    )
    game.run()


if __name__ == "__main__":
    main()
