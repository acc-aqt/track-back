"""Entry point to start the TrackBack game server with WebSocket + REST support."""

import argparse
import logging
import os

from server.local_ip import get_local_ip
from server.server import Server


def parse_args() -> int:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the TrackBack game server.")
    parser.add_argument("--port", type=int)

    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "4200"))

    return port


def log_server_info(port: int) -> None:
    """Log info where the server is running."""
    if os.getenv("RENDER") == "true":
        logging.info("Running on Render")
    else:
        logging.info("Running locally")
        ip = get_local_ip()
        url = f"http://{ip}:{port}"
        logging.info("\nGame server running at: %s\n", url)


def main() -> None:
    """Parse args and start the server."""
    logging.basicConfig(level=logging.INFO)

    port = parse_args()
    server = Server()

    log_server_info(port)

    server.run(port=port)


if __name__ == "__main__":
    main()
