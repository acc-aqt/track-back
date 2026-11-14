"""Contains the SequentialStrategy class."""

from typing import TYPE_CHECKING, Any

from game.user import User

from .abstract_game_strategy import AbstractGameStrategy

if TYPE_CHECKING:
    from game.game_logic import GameLogic


class SequentialStrategy(AbstractGameStrategy):
    """Each user's turn one after another, each user guesses a different song."""

    def __init__(self, game_instance: "GameLogic") -> None:
        super().__init__(game_instance)
        self.current_player_index = 0

    def validate_turn(self, username: str) -> dict[str, str] | None:
        """Only the current player can make a guess."""
        if self._get_current_player().name != username:
            return {"type": "error", "message": f"It is not {username}'s turn."}
        return None

    def handle_turn_progression(self, _: str) -> dict[str, Any]:
        """Skip to next track and to the next active player.

        If no player is active, advance to the next player in order.
        """
        user_count = len(self.game.users)
        next_index = (self.current_player_index + 1) % user_count
        for offset in range(user_count):
            candidate = (self.current_player_index + 1 + offset) % user_count
            if self.game.users[candidate].is_active:
                next_index = candidate
                break
        self.current_player_index = next_index

        self.game.music_service.next_track()
        return {"next_player": self._get_current_player().name}

    def get_players_to_notify_for_next_turn(self) -> list[User]:
        """Return a list of players to notify for the next turn."""
        return [self._get_current_player()]

    def _get_current_player(self) -> User:
        """Get the current player."""
        return self.game.users[self.current_player_index]
