from typing import Any

from game.user import User

from .abstract_game_strategy import AbstractGameStrategy


class SequentialStrategy(AbstractGameStrategy):
    
    def __init__(self, game):
        super().__init__(game)
        self.current_turn_index = 0
    def validate_turn(self, username: str) -> dict[str, str] | None:
        if self._get_current_player().name != username:
            return {"type": "error", "message": f"It is not {username}'s turn."}
        return None

    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        self.current_turn_index = (self.current_turn_index + 1) % len(
            self.game.users
        )
        self.game.music_service.next_track()
        return {"next_player": self._get_current_player().name}

    def get_players_to_notify(self) -> list[User]:
        return [self._get_current_player()]
    
    def _get_current_player(self) -> User:
        """Get the current player."""
        return self.game.users[self.current_turn_index]
