"""Entry point to start the track-back server."""

from dotenv import load_dotenv
import tomllib
from music_providers.factory import MusicProviderFactory
from music_providers.abstract_music_provider import AbstractMusicProvider
from game.user import get_users
from game.track_back_game import TrackBackGame


def load_user_config(path="config.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def main():
    """Main entry point to start the game."""
    load_dotenv()  # load credentials from .env file

    config = load_user_config()

    provider = config.get("music_provider")
    music_provider = MusicProviderFactory.create_music_provider(provider)
    music_provider.start_playback()

    users = get_users()

    target_song_count = config.get("target_song_count")
    game = TrackBackGame(
        users=users, target_song_count=target_song_count, music_provider=music_provider
    )
    game.run()


if __name__ == "__main__":
    main()
