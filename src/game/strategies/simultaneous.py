from typing import Any

from game.user import User

from .abstract_game_strategy import AbstractGameStrategy


class SimultaneousStrategy(AbstractGameStrategy):
    def validate_turn(self, username: str) -> dict[str, str] | None:
        if username in self.game.users_already_guessed:
            return {
                "type": "error",
                "message": f"⚠️ {username} has already guessed this song.",
            }
        return None

    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        self.game.users_already_guessed.add(username)

        if len(self.game.users_already_guessed) == len(self.game.users):
            self.game.music_service.next_track()
            self.game.users_already_guessed.clear()

        return {"next_player": None}

    def get_players_to_notify(self) -> list[User]:
        if len(self.game.users_already_guessed) == 0:
            return self.game.users
        else:
            return []
