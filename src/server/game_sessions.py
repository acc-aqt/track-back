"""Module with the GameSession and GameSessionManager classes."""

from fastapi import HTTPException, status

from game.game_logic import GameLogic  # or wherever your GameLogic class is
from server.connection_manager import ConnectionManager


class GameSession:
    """Holds the game logic and connection manager."""

    def __init__(self, game_logic: GameLogic) -> None:
        self.game_logic = game_logic
        self.connection_manager = ConnectionManager()


class GameSessionManager:
    """Holds all game sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}

    def add_game(self, game_id: str, game: GameLogic) -> None:
        """Create and store a full GameLogic instance."""
        if game_id in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session '{game_id}' already exists. Choose different ID.",
            )
        self.sessions[game_id] = GameSession(game)

    def get_game_session(self, game_id: str) -> GameSession | None:
        """Retrieve the game session by ID."""
        return self.sessions.get(game_id)

    def remove_game_session(self, game_id: str) -> None:
        """Remove a game session by ID."""
        if game_id in self.sessions:
            del self.sessions[game_id]


# Global instance (singleton)
game_session_manager = GameSessionManager()
