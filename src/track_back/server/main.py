"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os
from pathlib import Path

from track_back import __version__
from track_back.server import config, init_config
from track_back.server.server import Server


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument(
        "--version", action="version", version=f"track-back-server {__version__}"
    )
    subcommands = parser.add_subparsers(dest="command", title="commands")
    subcommands.add_parser("init", help="Interactively create the user config file.")
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
    return parser


def parse_args() -> tuple[int, int]:
    """Parse command line arguments for starting the server."""
    parser = build_parser()
    return server_settings(parser, parser.parse_args())


def server_settings(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> tuple[int, int]:
    """Load config and return the port and log level to start the server with."""
    if args.env_file is not None and not args.env_file.is_file():
        parser.error(f"env file not found: {args.env_file}")
    config.load_config(args.env_file)

    port = args.port or int(os.environ.get("PORT", "4200"))
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    return port, log_level


def main() -> None:
    """Run the chosen subcommand, or start the server when none is given."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init":
        init_config.run()
        return

    port, log_level = server_settings(parser, args)
    logging.basicConfig(level=log_level)

    server = Server()
    server.run(port=port)


if __name__ == "__main__":
    main()
