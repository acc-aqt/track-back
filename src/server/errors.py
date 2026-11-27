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
