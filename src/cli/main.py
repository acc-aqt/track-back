"""Entry point for the command line client of the TrackBack game."""

import argparse
import asyncio

from cli.client import play_on_cli


def parse_args() -> tuple[str, str, int]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Call command line client for the TrackBack game"
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Your username",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=4200, help="Server port (default: 4200)"
    )

    args = parser.parse_args()
    return args.name, args.host, args.port


def main() -> None:
    """Parse command line arguments and start the client."""
    username, host, port = parse_args()

    username = username or input("👤 Enter your username: ")

    asyncio.run(play_on_cli(username, host, port))


if __name__ == "__main__":
    main()
