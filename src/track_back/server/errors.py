"""Domain errors raised by the session and connection layer."""


class PlayerAlreadyRegisteredError(Exception):
    """A player with this name is already registered in the session."""

    def __init__(self, username: str) -> None:
        super().__init__(f"Player '{username}' already registered")


class NotEnoughPlayersError(Exception):
    """The Lobby has no Players to start the game with."""

    def __init__(self) -> None:
        super().__init__("Not enough players to start the game.")


class GameSessionNotFoundError(Exception):
    """No Game Session has this name."""

    def __init__(self, session_name: str) -> None:
        super().__init__(f"Game session {session_name} not found.")


class GameSessionOverError(Exception):
    """The Game Session already has a Winner."""

    def __init__(self, session_name: str, winner: str) -> None:
        super().__init__(f"Game session {session_name} is already over.")
        self.winner = winner


class SessionAlreadyExistsError(Exception):
    """A game session with this name already exists."""

    def __init__(self, session_name: str) -> None:
        super().__init__(
            f"Game session '{session_name}' already exists. Choose a different name."
        )


class PlayersNotConnectedError(Exception):
    """Some registered players have no live connection."""

    def __init__(self, usernames: list[str]) -> None:
        super().__init__(f"Players not connected: {', '.join(usernames)}.")


class NotAPlayerError(Exception):
    """The name is not a player of the running game."""

    def __init__(self, username: str, session_name: str, joinable: list[str]) -> None:
        super().__init__(
            f"Player '{username}' is not a player in game session {session_name}. "
            f"{_joinable_hint(joinable)}"
        )


class AlreadyConnectedError(Exception):
    """The player already holds a live connection to the running game."""

    def __init__(self, username: str, session_name: str, joinable: list[str]) -> None:
        super().__init__(
            f"Player '{username}' is already connected to game session {session_name}. "
            f"{_joinable_hint(joinable)}"
        )


def _joinable_hint(joinable: list[str]) -> str:
    return f"Only one of the following players can rejoin: {', '.join(joinable)}."
