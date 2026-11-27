"""Defines the server-to-client message vocabulary and shared message builders."""

from enum import StrEnum
from typing import Any

from track_back.game.game_logic import GuessResult
from track_back.game.player import Player
from track_back.game.song import Song


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


def welcome_message(username: str) -> dict[str, Any]:
    """Build the message confirming a player's connection."""
    return {
        "type": MessageType.WELCOME,
        "message": f"Welcome {username}, you're connected.",
    }


def error_message(message: str) -> dict[str, Any]:
    """Build the message telling a player what went wrong."""
    return {"type": MessageType.ERROR, "message": message}


def guess_request_message(
    player: Player, message: str = GUESS_REQUEST_TEXT
) -> dict[str, Any]:
    """Build the message asking a player to place the current song."""
    return {
        "type": MessageType.GUESS_REQUEST,
        "message": message,
        "next_player": player.name,
        "song_list": _timeline(player.timeline),
    }


def guess_result_message(result: GuessResult) -> dict[str, Any]:
    """Build the message telling the guessing player how their Guess went."""
    winner = result.winner.name if result.winner else ""
    return {
        "type": MessageType.GUESS_RESULT,
        "player": result.player.name,
        "result": _result_word(result),
        "message": f"Song was {result.song}.",
        "other_players": [_player_entry(other) for other in result.other_players],
        "last_index": str(result.position),
        "last_song": result.song.serialize(),
        "song_list": _timeline(result.player.timeline),
        "game_over": bool(winner),
        "winner": winner,
    }


def other_player_guess_message(result: GuessResult) -> dict[str, Any]:
    """Build the message telling the other players that someone guessed."""
    username = result.player.name
    outcome = _result_word(result)
    return {
        "type": MessageType.OTHER_PLAYER_GUESS,
        "player": username,
        "result": outcome,
        "message": f"{username} made a guess. Guess was {outcome}.",
    }


def player_disconnected_message(username: str) -> dict[str, Any]:
    """Build the message announcing that a player's connection dropped."""
    return {
        "type": MessageType.PLAYER_DISCONNECTED,
        "message": f"{username} disconnected. {username} can try to re-join the game.",
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
        "song_list": _timeline(player.timeline),
        "user_name": player.name,
    }


def _players_summary(player_names: list[str]) -> str:
    return f"There are now {len(player_names)} players: {', '.join(player_names)}."


def _result_word(result: GuessResult) -> str:
    return "correct" if result.correct else "wrong"


def _timeline(songs: list[Song]) -> list[dict[str, str | int]]:
    return [song.serialize() for song in songs]


def _player_entry(player: Player) -> dict[str, Any]:
    return {"name": player.name, "song_list": _timeline(player.timeline)}
