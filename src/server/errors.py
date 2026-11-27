"""Domain errors raised by the session and connection layer."""


class UserAlreadyRegisteredError(Exception):
    """A user with this name is already registered in the session."""

    def __init__(self, username: str) -> None:
        super().__init__(f"User '{username}' already registered")


class UserNotRegisteredError(Exception):
    """No user with this name is registered in the session."""

    def __init__(self, username: str) -> None:
        super().__init__(f"User '{username}' not registered.")


class SessionAlreadyExistsError(Exception):
    """A game session with this ID already exists."""

    def __init__(self, game_id: str) -> None:
        super().__init__(f"Session '{game_id}' already exists. Choose different ID.")


class PlayersNotConnectedError(Exception):
    """Some registered players have no live connection."""

    def __init__(self, usernames: list[str]) -> None:
        super().__init__(f"Players not connected: {', '.join(usernames)}.")


class NotAMemberError(Exception):
    """The name is not a member of the running game."""

    def __init__(self, username: str, game_id: str, joinable: list[str]) -> None:
        super().__init__(
            f"User '{username}' is not member in game session {game_id}. "
            f"{_joinable_hint(joinable)}"
        )


class AlreadyConnectedError(Exception):
    """The member already holds a live connection to the running game."""

    def __init__(self, username: str, game_id: str, joinable: list[str]) -> None:
        super().__init__(
            f"User '{username}' is already connected to game session {game_id}. "
            f"{_joinable_hint(joinable)}"
        )


def _joinable_hint(joinable: list[str]) -> str:
    return f"Only one of the following users can be connected: {', '.join(joinable)}."
