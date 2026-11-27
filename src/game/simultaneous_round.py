"""Contains the SimultaneousRound class."""


class SimultaneousRound:
    """Tracks who has guessed the song every player is placing this round."""

    def __init__(self) -> None:
        self.users_already_guessed: set[str] = set()

    def has_guessed(self, username: str) -> bool:
        """Return True if the user already guessed the current song."""
        return username in self.users_already_guessed

    def record_guess(self, username: str) -> None:
        """Remember that the user guessed the current song."""
        self.users_already_guessed.add(username)

    def is_complete(self, active_usernames: set[str]) -> bool:
        """Return True if there are active users and all of them have guessed."""
        return bool(active_usernames) and active_usernames <= self.users_already_guessed

    def start_next(self) -> None:
        """Forget this round's guesses."""
        self.users_already_guessed.clear()
