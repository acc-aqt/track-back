"""Defines the server-to-client message vocabulary and shared message builders."""

from enum import StrEnum
from typing import Any

from game.user import User


class MessageType(StrEnum):
    """Type of a message the server sends over the WebSocket."""

    WELCOME = "welcome"
    YOUR_TURN = "your_turn"
    GUESS_RESULT = "guess_result"
    OTHER_PLAYER_GUESS = "other_player_guess"
    PLAYER_JOINED = "player_joined"
    PLAYER_REJOINED = "player_rejoined"
    USER_DISCONNECTED = "user_disconnected"
    GAME_OVER = "game_over"
    ERROR = "error"


def your_turn_message(player: User, message: str = "It's your turn!") -> dict[str, Any]:
    """Build the message asking a player to place the current song."""
    return {
        "type": MessageType.YOUR_TURN,
        "message": message,
        "next_player": player.name,
        "song_list": [song.serialize() for song in player.song_list],
    }
