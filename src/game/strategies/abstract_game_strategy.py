from abc import ABC, abstractmethod
from typing import Any

from game.user import User


class AbstractGameStrategy(ABC):
    def __init__(self, game: "TrackBackGame") -> None:
        self.game = game

    @abstractmethod
    def validate_turn(self, username: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_players_to_notify(self) -> list[User]:
        pass
