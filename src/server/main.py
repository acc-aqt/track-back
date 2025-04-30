"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os

from server.server import Server


def parse_args() -> int:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument("--port", type=int)

    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "4200"))

    return port


def main() -> None:
    """Parse args and start the server."""
    logging.basicConfig(level=logging.INFO)

    port = parse_args()
    server = Server()

    server.run(port=port)


if __name__ == "__main__":
    main()
