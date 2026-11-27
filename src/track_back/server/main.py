"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os
from pathlib import Path

from track_back.server import config
from track_back.server.server import Server


def parse_args() -> tuple[int, int]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument("--port", type=int, help="Port to run the server on.")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Load config from this dotenv file before .env and the user config.",
    )

    args = parser.parse_args()

    if args.env_file is not None and not args.env_file.is_file():
        parser.error(f"env file not found: {args.env_file}")
    config.load_config(args.env_file)

    port = args.port or int(os.environ.get("PORT", "4200"))
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    return port, log_level


def main() -> None:
    """Parse args and start the server."""
    port, log_level = parse_args()
    logging.basicConfig(level=log_level)

    server = Server()
    server.run(port=port)


if __name__ == "__main__":
    main()
