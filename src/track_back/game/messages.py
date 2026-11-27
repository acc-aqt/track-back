"""Defines the server-to-client message vocabulary and shared message builders."""

from enum import StrEnum
from typing import Any

from track_back.game.player import Player


class MessageType(StrEnum):
    """Type of a message the server sends over the WebSocket."""

    WELCOME = "welcome"
    GUESS_REQUEST = "your_turn"
    GUESS_RESULT = "guess_result"
    OTHER_PLAYER_GUESS = "other_player_guess"
    PLAYER_JOINED = "player_joined"
    PLAYER_REJOINED = "player_rejoined"
    PLAYER_DISCONNECTED = "user_disconnected"
    GAME_OVER = "game_over"
    ERROR = "error"


GUESS_REQUEST_TEXT = "Place the new Song in your Timeline!"
NEW_ROUND_TEXT = "New round! Make your guess!"


def guess_request_message(
    player: Player, message: str = GUESS_REQUEST_TEXT
) -> dict[str, Any]:
    """Build the message asking a player to place the current song."""
    return {
        "type": MessageType.GUESS_REQUEST,
        "message": message,
        "next_player": player.name,
        "song_list": [song.serialize() for song in player.timeline],
    }


def game_over_message(winner: str) -> dict[str, Any]:
    """Build the message announcing the winner of the game."""
    return {
        "type": MessageType.GAME_OVER,
        "winner": winner,
        "message": f"{winner} has won the game!",
    }


def player_joined_message(user_name: str, player_names: list[str]) -> dict[str, Any]:
    """Build the message announcing a new player in the lobby."""
    return {
        "type": MessageType.PLAYER_JOINED,
        "message": f"{user_name} joined the game! {_players_summary(player_names)}",
        "user_name": user_name,
    }


def player_rejoined_message(player: Player, player_names: list[str]) -> dict[str, Any]:
    """Build the message announcing a player back in the running game."""
    return {
        "type": MessageType.PLAYER_REJOINED,
        "message": f"{player.name} re-joined the game! {_players_summary(player_names)}",
        "song_list": [song.serialize() for song in player.timeline],
        "user_name": player.name,
    }


def _players_summary(player_names: list[str]) -> str:
    return f"There are now {len(player_names)} players: {', '.join(player_names)}."
