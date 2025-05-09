"""Contains the factory and enum-class to creating the desired game strategies."""

from enum import Enum
from typing import TYPE_CHECKING

from .abstract_game_strategy import AbstractGameStrategy
from .sequential import SequentialStrategy
from .simultaneous import SimultaneousStrategy

if TYPE_CHECKING:
    from game.game_logic import GameLogic


class GameStrategyEnum(Enum):
    """Enum containing the game modes."""

    SEQUENTIAL = "sequential"
    SIMULTANEOUS = "simultaneous"


class GameStrategyFactory:
    """Creates game strategy based on the provided name."""

    @staticmethod
    def create_game_strategy(
        game_mode: GameStrategyEnum,
        game_instance: "GameLogic",
    ) -> AbstractGameStrategy:
        """Create a music service adapter based on the provided name."""
        if game_mode == GameStrategyEnum.SIMULTANEOUS:
            return SimultaneousStrategy(game_instance)

        if game_mode == GameStrategyEnum.SEQUENTIAL:
            return SequentialStrategy(game_instance)

        raise ValueError(
            f"Game mode {game_mode} is not supported. "
            f"Supported game modes are: "
            f"{', '.join([mode.value for mode in GameStrategyEnum])}"
        )
