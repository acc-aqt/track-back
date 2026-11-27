"""Contains the WebSocket handler for the game server."""

import json
import logging

from fastapi import WebSocket

from track_back.game.game_logic import GameLogic, GuessRejected
from track_back.music_service.error import MusicServiceError
from track_back.server.connection_manager import ConnectionManager
from track_back.server.game_sessions import GameSession
from track_back.server.messages import (
    NEW_ROUND_TEXT,
    MessageType,
    error_message,
    game_over_message,
    guess_request_message,
    guess_result_message,
    other_player_guess_message,
    welcome_message,
)

logger = logging.getLogger(__name__)


async def send_ws_message(ws: WebSocket, msg_type: MessageType, message: str) -> None:
    """Send a message to the WebSocket client."""
    await ws.send_text(json.dumps({"type": msg_type, "message": message}))


async def notify_players_owing_guess(
    connection_manager: ConnectionManager, game: GameLogic, message: str
) -> None:
    """Send your_turn to every connected player who still owes a guess."""
    for player in game.players_owing_guess():
        if websocket := connection_manager.get_websocket(player.name):
            await websocket.send_text(
                json.dumps(guess_request_message(player, message))
            )
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
        await websocket.send_text(json.dumps(welcome_message(username)))
        self.session.connect(username, websocket)

    async def handle_guess(
        self, websocket: WebSocket, username: str, index: int
    ) -> None:
        """Handle a guess from a player."""
        game = self.session.game_logic
        try:
            result = game.handle_guess(username, index)
        except MusicServiceError as e:
            await send_ws_message(websocket, MessageType.ERROR, str(e))
            return

        if isinstance(result, GuessRejected):
            await websocket.send_text(json.dumps(error_message(result.reason)))
            return

        await websocket.send_text(json.dumps(guess_result_message(result)))
        await self.connection_manager.broadcast(
            other_player_guess_message(result), exclude=username
        )

        if result.winner is not None:
            await self.connection_manager.broadcast(
                game_over_message(result.winner.name)
            )
        elif result.round_complete:
            await notify_players_owing_guess(
                self.connection_manager, game, NEW_ROUND_TEXT
            )
