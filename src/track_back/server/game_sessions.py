"""Module with the GameSession and GameSessionManager classes."""

import time

from track_back.game.game_logic import GameLogic
from track_back.game.player import Player
from track_back.server.connection_manager import ClientConnection, ConnectionManager
from track_back.server.errors import (
    AlreadyConnectedError,
    NotAPlayerError,
    SessionAlreadyExistsError,
)

EMPTY_SESSION_GRACE_PERIOD_SECONDS = 10 * 60


class GameSession:
    """Holds the game logic and connection manager."""

    def __init__(self, session_name: str, game_logic: GameLogic) -> None:
        self.session_name = session_name
        self.game_logic = game_logic
        self.connection_manager = ConnectionManager()
        self.empty_since: float | None = None

    def connect(self, username: str, websocket: ClientConnection) -> None:
        """Attach the player's live socket and count them as connected again."""
        if not self.connection_manager.player_is_registered(username):
            self.connection_manager.register_player(username)
        self.connection_manager.set_websocket(username, websocket)
        self.game_logic.player_rejoined(username)

    def disconnect(self, username: str) -> bool:
        """Drop the player's socket and mark them disconnected; return True if the round advanced."""
        self.connection_manager.unregister_player(username)
        return self.game_logic.player_disconnected(username)

    def check_can_rejoin(self, username: str) -> Player:
        """Return the player of the running game, unless unknown or connected."""
        player = self.game_logic.get_player(username)
        joinable = self.game_logic.disconnected_player_names()
        if player is None:
            raise NotAPlayerError(username, self.session_name, joinable)
        if player.is_connected:
            raise AlreadyConnectedError(username, self.session_name, joinable)
        return player


class GameSessionManager:
    """Holds all game sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}
        self.clock = time.monotonic

    def add_session(self, session_name: str, game: GameLogic) -> None:
        """Create and store a full GameLogic instance."""
        if session_name in self.sessions:
            raise SessionAlreadyExistsError(session_name)
        self.sessions[session_name] = GameSession(session_name, game)

    def get_game_session(self, session_name: str) -> GameSession | None:
        """Retrieve the game session by ID."""
        return self.sessions.get(session_name)

    def remove_game_session(self, session_name: str) -> None:
        """Remove a game session by ID."""
        if session_name in self.sessions:
            del self.sessions[session_name]

    def mark_empty(self, session: GameSession) -> None:
        """Record that the session's last connection has left."""
        session.empty_since = self.clock()

    def remove_expired_sessions(self) -> None:
        """Remove sessions that have been empty for longer than the grace period."""
        for session_name, session in list(self.sessions.items()):
            if self._is_expired(session):
                del self.sessions[session_name]

    def _is_expired(self, session: GameSession) -> bool:
        if session.empty_since is None or session.connection_manager.player_connections:
            return False
        empty_for = self.clock() - session.empty_since
        return empty_for > EMPTY_SESSION_GRACE_PERIOD_SECONDS


game_session_manager = GameSessionManager()
