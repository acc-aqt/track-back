"""Contains the ConnectionManager class, which handles player connections."""

import json
from enum import Enum
from typing import Any, Protocol

from track_back.server.errors import (
    PlayerAlreadyRegisteredError,
    PlayerNotRegisteredError,
)


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
    """Holds the registered players and websocket connections."""

    def __init__(self) -> None:
        self.player_connections: dict[str, ClientConnection | None] = {}

    def player_is_registered(self, username: str) -> bool:
        """Check if a player is already registered."""
        return username in self.player_connections

    def get_registered_player_names(self) -> list[str]:
        """Get a list of registered usernames."""
        return list(self.player_connections.keys())

    def register_player(self, username: str) -> None:
        """Register a new player."""
        if username in self.player_connections:
            raise PlayerAlreadyRegisteredError(username)
        self.player_connections[username] = None

    def unregister_player(self, username: str) -> None:
        """Unregister a player."""
        self._ensure_registered(username)
        self.player_connections.pop(username)

    async def broadcast(
        self, message: dict[str, Any], exclude: str | None = None
    ) -> None:
        """Send a message to every connected player except the excluded one."""
        text = json.dumps(message)
        for username, websocket in list(self.player_connections.items()):
            if username != exclude and websocket and self.is_connected(username):
                await websocket.send_text(text)

    def is_connected(self, username: str) -> bool:
        """Return True if the player holds a live connection."""
        websocket = self.player_connections.get(username)
        return websocket is not None and websocket.client_state.name == "CONNECTED"

    def get_unconnected_player_names(self) -> list[str]:
        """Get the registered usernames without a live connection."""
        return [
            username
            for username in self.player_connections
            if not self.is_connected(username)
        ]

    def set_websocket(self, username: str, websocket: ClientConnection) -> None:
        """Set the WebSocket connection for a player."""
        self._ensure_registered(username)
        self.player_connections[username] = websocket

    def get_websocket(self, username: str) -> ClientConnection | None:
        """Get the WebSocket connection for a given username."""
        return self.player_connections.get(username)

    def remove_websocket(self, username: str) -> None:
        """Remove the WebSocket connection for a player."""
        self._ensure_registered(username)
        self.player_connections[username] = None

    def _ensure_registered(self, username: str) -> None:
        if username not in self.player_connections:
            raise PlayerNotRegisteredError(username)
