"""Contains the ConnectionManager class, which delivers messages to live connections."""

import json
import logging
from enum import Enum
from typing import Protocol

from track_back.server.messages import OutgoingMessage

logger = logging.getLogger(__name__)


class ClientConnection(Protocol):
    """The parts of a client connection the server relies on."""

    @property
    def client_state(self) -> Enum:
        """Return the connection state."""
        ...

    async def send_text(self, data: str) -> None:
        """Send a text frame to the client."""
        ...


class ConnectionManager:
    """Maps Usernames to their live connections and delivers messages to them."""

    def __init__(self) -> None:
        self.connections: dict[str, ClientConnection] = {}

    def attach(self, username: str, connection: ClientConnection) -> None:
        """Remember the Player's live connection."""
        self.connections[username] = connection

    def detach(self, username: str, connection: ClientConnection) -> bool:
        """Forget this connection of the Player; return False if a newer one replaced it."""
        if self.connections.get(username) is not connection:
            return False
        del self.connections[username]
        return True

    async def deliver(self, outgoing: list[OutgoingMessage]) -> None:
        """Send each message to the live connections it is addressed to."""
        for message in outgoing:
            text = json.dumps(message.message)
            for username in self._recipients(message):
                if connection := self._live_connection(username):
                    await connection.send_text(text)
                else:
                    logger.warning("Player %s has no live connection.", username)

    def _recipients(self, message: OutgoingMessage) -> list[str]:
        if message.to is not None:
            return [message.to]
        return [
            username for username in self.connections if username != message.exclude
        ]

    def _live_connection(self, username: str) -> ClientConnection | None:
        connection = self.connections.get(username)
        if connection is None or connection.client_state.name != "CONNECTED":
            return None
        return connection
