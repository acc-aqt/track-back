"""Contains the WebSocket handler for the game server."""

import json
import logging

from fastapi import WebSocket

from game.game_logic import GameLogic
from game.messages import MessageType, your_turn_message
from game.user import User
from music_service.error import MusicServiceError
from server.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


async def send_ws_message(ws: WebSocket, msg_type: MessageType, message: str) -> None:
    """Send a message to the WebSocket client."""
    await ws.send_text(json.dumps({"type": msg_type, "message": message}))


class WebSocketGameHandler:
    """WebSocket handler for managing game connections and interactions."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def handle_connection(self, websocket: WebSocket, username: str) -> None:
        """Handle a new WebSocket connection for a player."""
        if not self.connection_manager.user_is_registered(username):
            self.connection_manager.register_user(username)
        await send_ws_message(
            websocket,
            MessageType.WELCOME,
            f"Welcome {username}, you're connected.",
        )

        self.connection_manager.set_websocket(username, websocket)

    async def handle_guess(
        self, websocket: WebSocket, username: str, index: int, game: GameLogic
    ) -> None:
        """Handle a guess from a player."""
        try:
            payload = game.handle_player_turn(username, index)
        except MusicServiceError as e:
            await send_ws_message(websocket, MessageType.ERROR, str(e))
            return

        await websocket.send_text(json.dumps(payload))
        if payload["type"] == MessageType.ERROR:
            return

        if payload["type"] == MessageType.GUESS_RESULT:
            await self.connection_manager.broadcast(
                {
                    "type": MessageType.OTHER_PLAYER_GUESS,
                    "player": username,
                    "result": payload["result"],
                    "message": f"{username} made a guess. "
                    f"Guess was {payload['result']}.",
                    "next_player": payload.get("next_player"),
                },
                exclude=username,
            )

        await self.notify_next_round(game)

        if payload.get("game_over"):
            winner = payload["winner"]
            await self.connection_manager.broadcast(
                {
                    "type": MessageType.GAME_OVER,
                    "winner": winner,
                    "message": f"{winner} has won the game!",
                }
            )

    async def notify_next_round(self, game: GameLogic) -> None:
        """Send your_turn to every player owed a card for a newly started round."""
        for player in game.round.get_players_to_notify_for_next_turn():
            await self._notify_for_next_turn(player)

    async def _notify_for_next_turn(self, player: User) -> None:
        if websocket := self.connection_manager.get_websocket(player.name):
            message = your_turn_message(player, "New round! Make your guess!")
            await websocket.send_text(json.dumps(message))
        else:
            logger.warning(
                "Player %s has no WebSocket; they are notified on reconnect.",
                player.name,
            )
