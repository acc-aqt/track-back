"""Contains the SimultaneousRound class."""


class SimultaneousRound:
    """Tracks who has guessed the song every player is placing this round."""

    def __init__(self) -> None:
        self.players_already_guessed: set[str] = set()

    def has_guessed(self, username: str) -> bool:
        """Return True if the player already guessed the current song."""
        return username in self.players_already_guessed

    def record_guess(self, username: str) -> None:
        """Remember that the player guessed the current song."""
        self.players_already_guessed.add(username)

    def is_complete(self, connected_usernames: set[str]) -> bool:
        """Return True if there are connected players and all of them have guessed."""
        return (
            bool(connected_usernames)
            and connected_usernames <= self.players_already_guessed
        )

    def start_next(self) -> None:
        """Forget this round's guesses."""
        self.players_already_guessed.clear()
