"""Contains the SimultaneousRound class."""

from typing import TYPE_CHECKING, Any

from game.messages import MessageType
from game.user import User

if TYPE_CHECKING:
    from game.game_logic import GameLogic


class SimultaneousRound:
    """Implements rounds in which all players guess on the same song."""

    def __init__(self, game: "GameLogic") -> None:
        self.game = game
        self.users_already_guessed: set[str] = set()

    def validate_turn(self, username: str) -> dict[str, str] | None:
        """Only users who haven't guessed yet can make a guess."""
        if username in self.users_already_guessed:
            return {
                "type": MessageType.ERROR,
                "message": f"{username} has already guessed this song.",
            }
        return None

    def has_guessed(self, username: str) -> bool:
        """Return True if the user already guessed the current song."""
        return username in self.users_already_guessed

    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        """Only when every user has guessed, the game will skip to the next track."""
        self.users_already_guessed.add(username)
        self._advance_if_round_complete()
        return {"next_player": None}

    def player_left(self, username: str) -> bool:
        """Stop waiting for a departed player; return True if the round advanced."""
        if user := self.game.get_user(username):
            user.is_active = False
        return self._advance_if_round_complete()

    def _advance_if_round_complete(self) -> bool:
        active_users = {user.name for user in self.game.users if user.is_active}
        if not active_users or active_users - self.users_already_guessed:
            return False
        self.game.music_service.next_track()
        self.users_already_guessed.clear()
        return True

    def get_players_to_notify_for_next_turn(self) -> list[User]:
        """Return a list of players to notify for the next turn."""
        if len(self.users_already_guessed) == 0:
            return [user for user in self.game.users if user.is_active]
        return []
