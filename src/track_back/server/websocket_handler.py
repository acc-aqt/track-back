"""Contains the WebSocket handler for the game server."""

import json
import logging

from fastapi import WebSocket

from track_back.game.game_logic import GameLogic
from track_back.game.messages import (
    NEW_ROUND_TEXT,
    MessageType,
    game_over_message,
    your_turn_message,
)
from track_back.music_service.error import MusicServiceError
from track_back.server.connection_manager import ConnectionManager
from track_back.server.game_sessions import GameSession

logger = logging.getLogger(__name__)


async def send_ws_message(ws: WebSocket, msg_type: MessageType, message: str) -> None:
    """Send a message to the WebSocket client."""
    await ws.send_text(json.dumps({"type": msg_type, "message": message}))


async def notify_players_owed_card(
    connection_manager: ConnectionManager, game: GameLogic, message: str
) -> None:
    """Send your_turn to every connected player who still owes a guess."""
    for player in game.players_owed_card():
        if websocket := connection_manager.get_websocket(player.name):
            await websocket.send_text(json.dumps(your_turn_message(player, message)))
        else:
            logger.warning(
                "Player %s has no WebSocket; they are notified on reconnect.",
                player.name,
            )


class WebSocketGameHandler:
    """WebSocket handler for managing game connections and interactions."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.connection_manager = session.connection_manager

    async def handle_connection(self, websocket: WebSocket, username: str) -> None:
        """Handle a new WebSocket connection for a player."""
        await send_ws_message(
            websocket,
            MessageType.WELCOME,
            f"Welcome {username}, you're connected.",
        )
        self.session.connect(username, websocket)

    async def handle_guess(
        self, websocket: WebSocket, username: str, index: int
    ) -> None:
        """Handle a guess from a player."""
        game = self.session.game_logic
        try:
            result = game.handle_player_turn(username, index)
        except MusicServiceError as e:
            await send_ws_message(websocket, MessageType.ERROR, str(e))
            return

        payload = result.message
        await websocket.send_text(json.dumps(payload))
        if payload["type"] == MessageType.ERROR:
            return

        await self.connection_manager.broadcast(
            {
                "type": MessageType.OTHER_PLAYER_GUESS,
                "player": username,
                "result": payload["result"],
                "message": f"{username} made a guess. Guess was {payload['result']}.",
            },
            exclude=username,
        )

        if payload["game_over"]:
            await self.connection_manager.broadcast(
                game_over_message(payload["winner"])
            )
        elif result.round_complete:
            await notify_players_owed_card(
                self.connection_manager, game, NEW_ROUND_TEXT
            )
