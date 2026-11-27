"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os
import webbrowser
from pathlib import Path

from track_back import __version__
from track_back.server import config, init_config
from track_back.server.server import Server, uses_ssl

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open the Web UI in the default browser on start.",
    )
    return parser


def server_settings(args: argparse.Namespace) -> tuple[int, int]:
    """Load config and return the port and log level to start the server with."""
    config.load_config(args.env_file)

    port = args.port or int(os.environ.get("PORT", config.DEFAULT_PORT))
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    return port, log_level


def open_browser(url: str) -> None:
    """Open the URL in the default browser, logging a warning if that fails."""
    try:
        opened = webbrowser.open(url)
    except webbrowser.Error:
        opened = False
    if not opened:
        logger.warning("Could not open a browser. Open %s by hand.", url)


def main() -> None:
    """Run the chosen subcommand, or start the server when none is given."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init":
        init_config.run()
        return

    if args.env_file is not None and not args.env_file.is_file():
        parser.error(f"env file not found: {args.env_file}")
    port, log_level = server_settings(args)
    logging.basicConfig(level=log_level)

    server = Server()
    if not args.no_browser:
        scheme = "https" if uses_ssl() else "http"
        url = f"{scheme}://localhost:{port}/"
        server.call_when_ready(lambda: open_browser(url))
    server.run(port=port)


if __name__ == "__main__":
    main()
