"""Implements the interface for the game mode strategies tht can be injected."""

from abc import ABC, abstractmethod
from typing import Any

from game.user import User


class AbstractGameStrategy(ABC):
    """Use strategy pattern to inject different game modes."""

    def __init__(self, game_instance) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001
        self.game = game_instance

    @abstractmethod
    def validate_turn(self, username: str) -> dict[str, Any] | None:
        """Return an error message if the turn is invalid, otherwise None."""

    @abstractmethod
    def handle_turn_progression(self, username: str) -> dict[str, Any]:
        """Implement the logic for handling turn progression."""

    @abstractmethod
    def get_players_to_notify_for_next_turn(self) -> list[User]:
        """Return a list of players to notify for the next turn."""
