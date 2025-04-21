"""Contains the ConnectionManager class, which handles user connections."""

from fastapi import WebSocket

from game.user import User


class ConnectionManager:
    """Holds the registered users and websocket connections."""

    def __init__(self) -> None:
        self.registered_users: dict[str, User] = {}
        self.websockets: dict[str, WebSocket] = {}

        self.first_player: str | None = None

    def get_websocket(self, username: str) -> WebSocket | None:
        """Get the WebSocket connection for a given username."""
        return self.websockets.get(username)
