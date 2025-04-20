from enum import Enum

from .abstract_game_strategy import AbstractGameStrategy
from .sequential import SequentialStrategy
from .simultaneous import SimultaneousStrategy


class GameStrategyEnum(Enum):
    SEQUENTIAL = "sequential"
    SIMULTANEOUS = "simultaneous"


class GameStrategyFactory:
    """Creates game strategy based on the provided name."""

    @staticmethod
    def create_game_strategy(game_mode: GameStrategyEnum, game) -> AbstractGameStrategy:
        """Create a music service adapter based on the provided name."""
        if game_mode == GameStrategyEnum.SIMULTANEOUS:
            return SimultaneousStrategy(game)

        if game_mode == GameStrategyEnum.SEQUENTIAL:
            return SequentialStrategy(game)
