from game.game_logic import GameLogic  # or wherever your GameLogic class is
from server.connection_manager import ConnectionManager


class GameSession:
    """Holds the game logic and connection manager."""

    def __init__(self, game_logic: GameLogic):
        self.game_logic = game_logic
        self.connection_manager = (
            ConnectionManager()
        )  # 🔥 each game has its own connection manager


class GameSessionManager:
    """Holds all game sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}

    def add_game(self, game_id: str, game) -> None:
        """Create and store a full GameLogic instance."""
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
