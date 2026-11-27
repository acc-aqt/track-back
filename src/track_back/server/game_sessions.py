"""Module with the GameSession and GameSessionManager classes."""

import time
from collections.abc import Callable

from track_back.game.errors import GameAlreadyRunningError
from track_back.game.game_logic import GameLogic, GuessRejected
from track_back.game.player import Player
from track_back.server.connection_manager import ConnectionManager
from track_back.server.errors import (
    AlreadyConnectedError,
    GameSessionNotFoundError,
    GameSessionOverError,
    NotAPlayerError,
    NotEnoughPlayersError,
    PlayerAlreadyRegisteredError,
    PlayersNotConnectedError,
    SessionAlreadyExistsError,
)
from track_back.server.messages import (
    GUESS_REQUEST_TEXT,
    NEW_ROUND_TEXT,
    OutgoingMessage,
    error_message,
    game_over_message,
    guess_request_message,
    guess_result_message,
    other_player_guess_message,
    player_disconnected_message,
    player_joined_message,
    player_rejoined_message,
    to_everyone,
    to_everyone_except,
    to_player,
    welcome_message,
)

EMPTY_SESSION_GRACE_PERIOD_SECONDS = 10 * 60


class GameSession:
    """Owns the Lobby, Rejoin and Round rules of one Game Session.

    It keeps the one record of its Players, from the Lobby to the game's end.
    Operations return the messages to send instead of sending them; the
    ``connection_manager`` only holds the live connections that deliver them.
    """

    def __init__(self, session_name: str, game_logic: GameLogic) -> None:
        self.session_name = session_name
        self.game_logic = game_logic
        self.players: list[Player] = []
        self.connection_manager = ConnectionManager()
        self.empty_since: float | None = None

    @property
    def is_running(self) -> bool:
        """Return True between the start and the Winner."""
        return self.game_logic.running

    @property
    def is_over(self) -> bool:
        """Return True once a Player has won."""
        return self.game_logic.winner is not None

    @property
    def is_joinable(self) -> bool:
        """Return True for a Lobby, or a running game a Player can Rejoin."""
        if self.is_over:
            return False
        return not self.is_running or bool(self._disconnected_player_names())

    @property
    def has_connected_players(self) -> bool:
        """Return True if any Player is connected."""
        return any(player.is_connected for player in self.players)

    def join(self, username: str) -> list[OutgoingMessage]:
        """Add a Player to the Lobby, or check that they can Rejoin the game."""
        self._check_not_over()
        if self.is_running:
            self._rejoining_player(username)
            return []
        if self._player(username) is not None:
            raise PlayerAlreadyRegisteredError(username)
        self.players.append(Player(username, is_connected=False))
        return [to_everyone(player_joined_message(username, self._player_names()))]

    def start(self) -> list[OutgoingMessage]:
        """Start the game and ask every Player for their first Guess."""
        self._check_not_over()
        if self.is_running:
            raise GameAlreadyRunningError(self.session_name)
        if not self.players:
            raise NotEnoughPlayersError
        if unconnected := self._disconnected_player_names():
            raise PlayersNotConnectedError(unconnected)
        # The game logic shares this record of Players for the rest of the game.
        self.game_logic.start_game(self.players)
        return self._guess_requests(GUESS_REQUEST_TEXT)

    def connect(self, username: str) -> list[OutgoingMessage]:
        """Count a Player's new connection: a first connection or a Rejoin."""
        self._check_not_over()
        welcome = to_player(username, welcome_message(username))
        if not self.is_running:
            player = self._player(username)
            if player is None:
                self.players.append(Player(username))
            else:
                player.is_connected = True
            return [welcome]

        player = self._rejoining_player(username)
        player.is_connected = True
        rejoined = player_rejoined_message(player, self._player_names())
        if self.game_logic.owes_guess(username):
            return [
                welcome,
                to_player(username, guess_request_message(player)),
                to_everyone_except(username, rejoined),
            ]
        return [welcome, to_everyone(rejoined)]

    def guess(self, username: str, index: int) -> list[OutgoingMessage]:
        """Judge a Player's Guess and tell everyone how it went."""
        result = self.game_logic.handle_guess(username, index)
        if isinstance(result, GuessRejected):
            return [to_player(username, error_message(result.reason))]

        outgoing = [
            to_player(username, guess_result_message(result)),
            to_everyone_except(username, other_player_guess_message(result)),
        ]
        if result.winner is not None:
            outgoing.append(to_everyone(game_over_message(result.winner.name)))
        elif result.round_complete:
            outgoing.extend(self._guess_requests(NEW_ROUND_TEXT))
        return outgoing

    def disconnect(self, username: str) -> list[OutgoingMessage]:
        """Drop a Player from the Lobby, or mark them a Disconnected Player."""
        outgoing = [to_everyone(player_disconnected_message(username))]
        if not self.is_running and not self.is_over:
            self.players = [p for p in self.players if p.name != username]
            return outgoing
        if self.game_logic.player_disconnected(username):
            outgoing.extend(self._guess_requests(NEW_ROUND_TEXT))
        return outgoing

    def _check_not_over(self) -> None:
        if self.game_logic.winner is not None:
            raise GameSessionOverError(self.session_name, self.game_logic.winner.name)

    def _rejoining_player(self, username: str) -> Player:
        player = self._player(username)
        joinable = self._disconnected_player_names()
        if player is None:
            raise NotAPlayerError(username, self.session_name, joinable)
        if player.is_connected:
            raise AlreadyConnectedError(username, self.session_name, joinable)
        return player

    def _guess_requests(self, text: str) -> list[OutgoingMessage]:
        return [
            to_player(player.name, guess_request_message(player, text))
            for player in self.game_logic.players_owing_guess()
            if player.is_connected
        ]

    def _player(self, username: str) -> Player | None:
        return next((p for p in self.players if p.name == username), None)

    def _player_names(self) -> list[str]:
        return [player.name for player in self.players]

    def _disconnected_player_names(self) -> list[str]:
        return [player.name for player in self.players if not player.is_connected]


class GameSessionManager:
    """Holds all game sessions.

    Parameters
    ----------
    clock : Callable[[], float]
        Returns the current time in seconds; it times the Rejoin grace period.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.sessions: dict[str, GameSession] = {}
        self.clock = clock

    def add_session(self, session_name: str, game: GameLogic) -> None:
        """Create and store a full GameLogic instance."""
        if session_name in self.sessions:
            raise SessionAlreadyExistsError(session_name)
        self.sessions[session_name] = GameSession(session_name, game)

    def get_game_session(self, session_name: str) -> GameSession:
        """Return the Game Session with this name, or raise if there is none."""
        session = self.sessions.get(session_name)
        if session is None:
            raise GameSessionNotFoundError(session_name)
        return session

    def remove_game_session(self, session_name: str) -> None:
        """Remove a game session by ID."""
        if session_name in self.sessions:
            del self.sessions[session_name]

    def joinable_session_names(self) -> list[str]:
        """Return the names of the Game Sessions a Player can join or Rejoin."""
        self.remove_expired_sessions()
        return [name for name, session in self.sessions.items() if session.is_joinable]

    def release_if_empty(self, session: GameSession) -> None:
        """Keep an empty running game for Rejoin; remove an empty Lobby or finished game."""
        if session.has_connected_players:
            return
        if session.is_running:
            session.empty_since = self.clock()
        elif session.is_over or not session.players:
            self.remove_game_session(session.session_name)

    def remove_expired_sessions(self) -> None:
        """Remove sessions that have been empty for longer than the grace period."""
        for session_name, session in list(self.sessions.items()):
            if self._is_expired(session):
                del self.sessions[session_name]

    def _is_expired(self, session: GameSession) -> bool:
        if session.empty_since is None or session.has_connected_players:
            return False
        empty_for = self.clock() - session.empty_since
        return empty_for > EMPTY_SESSION_GRACE_PERIOD_SECONDS
