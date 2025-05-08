"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os

from dotenv import load_dotenv

from server.server import Server


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

    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "4200"))
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    return port, log_level


def main() -> None:
    """Parse args and start the server."""
    port, log_level = parse_args()
    logging.basicConfig(level=log_level)

    load_dotenv()
    server = Server()

    server.run(port=port)


if __name__ == "__main__":
    main()
