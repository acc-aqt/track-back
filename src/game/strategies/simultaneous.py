"""Contains the SimultaneousStrategy class."""

from typing import Any

from game.user import User

from .abstract_game_strategy import AbstractGameStrategy


class SimultaneousStrategy(AbstractGameStrategy):
    """Implements the game mode where all players guess on the same songs."""

    def __init__(self, game) -> None:  # noqa: ANN001
        super().__init__(game)
        self.users_already_guessed = set()

    def validate_turn(self, username: str) -> dict[str, str] | None:
        """Only users who haven't guessed yet can make a guess."""
        if username in self.users_already_guessed:
            return {
                "type": "error",
                "message": f"⚠️ {username} has already guessed this song.",
            }
        return None

    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        """Only when every user has guessed, the game will skip to the next track."""
        self.users_already_guessed.add(username)

        if len(self.users_already_guessed) == len(self.game.users):
            self.game.music_service.next_track()
            self.users_already_guessed.clear()

        return {"next_player": None}

    def get_players_to_notify_for_next_turn(self) -> list[User]:
        """Return a list of players to notify for the next turn."""
        if len(self.users_already_guessed) == 0:
            return self.game.users
        return []
