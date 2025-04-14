"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import tomllib
from pathlib import Path

from dotenv import load_dotenv

from backend.music_service.factory import MusicServiceFactory

from .server.game_context import GameContext
from .server.server import Server


def parse_args() -> tuple[int, int]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument("--target_song_count", type=int, default=10)
    parser.add_argument("--port", type=int, default=4200)
    args = parser.parse_args()
    return args.target_song_count, args.port


def load_user_config(config_path: str = "config.toml") -> dict[str, str]:
    """Load configuration values (e.g. music service provider) from TOML file."""
    with Path(config_path).open("rb") as f:
        return tomllib.load(f)


def main() -> None:
    """Command-line entry point for launching the server."""
    logging.basicConfig(level=logging.INFO)

    target_song_count, port = parse_args()

    load_dotenv()
    config = load_user_config()
    music_service = MusicServiceFactory.create_music_service(config["music_service"])

    game_context = GameContext(
        target_song_count=target_song_count,
        music_service=music_service,
    )

    server = Server(game_context=game_context, port=port)
    server.run()


if __name__ == "__main__":
    main()
