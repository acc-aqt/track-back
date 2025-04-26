"""Contains the ConnectionManager class, which handles user connections."""

from fastapi import HTTPException, WebSocket, status
from fastapi.responses import JSONResponse


class ConnectionManager:
    """Holds the registered users and websocket connections."""

    def __init__(self) -> None:
        self.user_connections: dict[str, WebSocket | None] = {}

        self.first_player: str | None = None

    def user_is_registered(self, username: str) -> bool:
        """Check if a user is already registered."""
        return username in self.user_connections

    def get_registered_user_names(self) -> list[str]:
        """Get a lis of registered usernames."""
        return list(self.user_connections.keys())

    def register_user(self, username: str) -> JSONResponse:
        """Register a new user."""
        if username in self.user_connections:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{username}' already registered",
            )

        self.user_connections[username] = None

        return JSONResponse(
            status_code=201,
            content={
                "message": f"User '{username}' registered successfully.",
                "user": username,
            },
        )

    def unregister_user(self, username: str) -> JSONResponse:
        """Unregister a user."""
        if username not in self.user_connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not registered.",
            )

        self.user_connections.pop(username)

        return JSONResponse(
            status_code=200,
            content={
                "message": "User '{username}' unregistered successfully.",
                "user": username,
            },
        )

    def get_all_websockets(self) -> list[WebSocket]:
        """Get all WebSocket connections."""
        return [websocket for websocket in self.user_connections.values() if websocket]

    def set_websocket(self, username: str, websocket: WebSocket) -> None:
        """Set the WebSocket connection for a user."""
        if username not in self.user_connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not registered.",
            )
        self.user_connections[username] = websocket

    def get_websocket(self, username: str) -> WebSocket | None:
        """Get the WebSocket connection for a given username."""
        return self.user_connections.get(username)

    def remove_websocket(self, username: str) -> None:
        """Remove the WebSocket connection for a user."""
        if username not in self.user_connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not registered.",
            )
        self.user_connections[username] = None
