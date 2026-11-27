"""Module with the GameSession and GameSessionManager classes."""

import time

from game.game_logic import GameLogic
from game.user import User
from server.connection_manager import ClientConnection, ConnectionManager
from server.errors import (
    AlreadyConnectedError,
    NotAMemberError,
    SessionAlreadyExistsError,
)

EMPTY_SESSION_GRACE_PERIOD_SECONDS = 10 * 60


class GameSession:
    """Holds the game logic and connection manager."""

    def __init__(self, game_id: str, game_logic: GameLogic) -> None:
        self.game_id = game_id
        self.game_logic = game_logic
        self.connection_manager = ConnectionManager()
        self.empty_since: float | None = None

    def connect(self, username: str, websocket: ClientConnection) -> None:
        """Attach the user's live socket and count a member as active again."""
        if not self.connection_manager.user_is_registered(username):
            self.connection_manager.register_user(username)
        self.connection_manager.set_websocket(username, websocket)
        self.game_logic.player_returned(username)

    def disconnect(self, username: str) -> bool:
        """Drop the user's socket and active flag; return True if the round advanced."""
        self.connection_manager.unregister_user(username)
        return self.game_logic.player_left(username)

    def check_can_rejoin(self, username: str) -> User:
        """Return the member of the running game, unless unknown or connected."""
        member = self.game_logic.get_user(username)
        joinable = self.game_logic.inactive_member_names()
        if member is None:
            raise NotAMemberError(username, self.game_id, joinable)
        if member.is_active:
            raise AlreadyConnectedError(username, self.game_id, joinable)
        return member


class GameSessionManager:
    """Holds all game sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}
        self.clock = time.monotonic

    def add_game(self, game_id: str, game: GameLogic) -> None:
        """Create and store a full GameLogic instance."""
        if game_id in self.sessions:
            raise SessionAlreadyExistsError(game_id)
        self.sessions[game_id] = GameSession(game_id, game)

    def get_game_session(self, game_id: str) -> GameSession | None:
        """Retrieve the game session by ID."""
        return self.sessions.get(game_id)

    def remove_game_session(self, game_id: str) -> None:
        """Remove a game session by ID."""
        if game_id in self.sessions:
            del self.sessions[game_id]

    def mark_empty(self, session: GameSession) -> None:
        """Record that the session's last connection has left."""
        session.empty_since = self.clock()

    def remove_expired_sessions(self) -> None:
        """Remove sessions that have been empty for longer than the grace period."""
        for game_id, session in list(self.sessions.items()):
            if self._is_expired(session):
                del self.sessions[game_id]

    def _is_expired(self, session: GameSession) -> bool:
        if session.empty_since is None or session.connection_manager.user_connections:
            return False
        empty_for = self.clock() - session.empty_since
        return empty_for > EMPTY_SESSION_GRACE_PERIOD_SECONDS


game_session_manager = GameSessionManager()
