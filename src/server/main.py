"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

from game.game_logic import GameLogic
from game.strategies.factory import GameStrategyEnum
from music_service.factory import MusicServiceFactory
from server.connection_manager import ConnectionManager
from server.local_ip import get_local_ip
from server.server import Server


def parse_args() -> tuple[int, int]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument("--target_song_count", type=int, default=10)
    parser.add_argument("--port", type=int)

    args = parser.parse_args()

    target_song_count = args.target_song_count

    port = args.port or int(os.environ.get("PORT", "4200"))

    return target_song_count, port


def load_user_config(config_path: str) -> dict[str, str]:
    """Load configuration values (e.g. music service provider) from TOML file."""
    with Path(config_path).open("rb") as f:
        return tomllib.load(f)


def log_server_info(port: int) -> None:
    """Log info where the server is running."""
    if os.getenv("RENDER") == "true":
        logging.info("Running on Render")
    else:
        logging.info("Running locally")
        ip = get_local_ip()
        url = f"http://{ip}:{port}"
        logging.info("\nGame server running at: %s\n", url)


def build_server(
    config_path: str,
    target_song_count: int,
) -> Server:
    """Parse args and start the server."""
    logging.basicConfig(level=logging.INFO)

    load_dotenv()
    config = load_user_config(config_path)

    music_service = MusicServiceFactory.create_music_service(config["music_service"])
    game_strategy_enum = GameStrategyEnum(config["game_mode"])

    game = GameLogic(
        target_song_count,
        music_service,
        game_strategy_enum,
    )

    connection_manager = ConnectionManager()

    server = Server(connection_manager=connection_manager, game=game)
    return server


def main() -> None:
    """Parse args and start the server."""
    target_song_count, port = parse_args()
    server = build_server(
        config_path="config.toml",
        target_song_count=target_song_count,
    )

    log_server_info(port)

    server.run(port=port)


if __name__ == "__main__":
    main()
