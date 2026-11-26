"""Contains the ConnectionManager class, which handles user connections."""

from enum import Enum
from typing import Protocol

from server.errors import UserAlreadyRegisteredError, UserNotRegisteredError


class ClientConnection(Protocol):
    """The parts of a client connection the game layer relies on."""

    @property
    def client_state(self) -> Enum:
        """Return the connection state."""
        ...

    async def send_text(self, data: str) -> None:
        """Send a text frame to the client."""
        ...


class ConnectionManager:
    """Holds the registered users and websocket connections."""

    def __init__(self) -> None:
        self.user_connections: dict[str, ClientConnection | None] = {}

    def user_is_registered(self, username: str) -> bool:
        """Check if a user is already registered."""
        return username in self.user_connections

    def get_registered_user_names(self) -> list[str]:
        """Get a list of registered usernames."""
        return list(self.user_connections.keys())

    def register_user(self, username: str) -> None:
        """Register a new user."""
        if username in self.user_connections:
            raise UserAlreadyRegisteredError(username)
        self.user_connections[username] = None

    def unregister_user(self, username: str) -> None:
        """Unregister a user."""
        self._ensure_registered(username)
        self.user_connections.pop(username)

    def get_all_websockets(self) -> list[ClientConnection]:
        """Get all WebSocket connections."""
        return [websocket for websocket in self.user_connections.values() if websocket]

    def set_websocket(self, username: str, websocket: ClientConnection) -> None:
        """Set the WebSocket connection for a user."""
        self._ensure_registered(username)
        self.user_connections[username] = websocket

    def get_websocket(self, username: str) -> ClientConnection | None:
        """Get the WebSocket connection for a given username."""
        return self.user_connections.get(username)

    def remove_websocket(self, username: str) -> None:
        """Remove the WebSocket connection for a user."""
        self._ensure_registered(username)
        self.user_connections[username] = None

    def _ensure_registered(self, username: str) -> None:
        if username not in self.user_connections:
            raise UserNotRegisteredError(username)
