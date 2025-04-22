"""Contains the WebSocket handler for the game server."""

import json
import os
import signal

from fastapi import WebSocket

from game.game_logic import GameLogic
from game.user import User
from server.connection_manager import ConnectionManager


async def send_ws_message(ws: WebSocket, msg_type: str, message: str) -> None:
    """Send a message to the WebSocket client."""
    await ws.send_text(json.dumps({"type": msg_type, "message": message}))


class WebSocketGameHandler:
    """WebSocket handler for managing game connections and interactions."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self.connection_manager = (
            connection_manager  # GameContext with game, users, sockets, etc.
        )

    async def handle_connection(self, websocket: WebSocket, username: str) -> None:
        """Handle a new WebSocket connection for a player."""
        if self.connection_manager.user_is_registered(username):
            await send_ws_message(websocket, "welcome", f"Welcome back, {username}!")

        else:
            self.connection_manager.register_user(username)
            await send_ws_message(
                websocket,
                "welcome",
                f"Welcome, {username}! You're connected.",
            )

        self.connection_manager.set_websocket(username, websocket)

    async def handle_guess(
        self, websocket: WebSocket, username: str, index: int, game: GameLogic
    ) -> None:
        """Handle a guess from a player."""
        payload = game.handle_player_turn(username, index)

        # Send result to the player who guessed
        await websocket.send_text(json.dumps(payload))
        if payload["type"] == "error":
            return

        if payload.get("game_over"):
            winner = payload["winner"]
            await self._broadcast_game_over(winner)
            self._terminate_process()
            return

        if payload["type"] == "guess_result":
            await self._broadcast_guess_to_other_players(
                current_player=username,
                message=f"{username} made his guess. (Guess was: {payload['result']})",
                result=payload,
            )

        players_to_notify = game.strategy.get_players_to_notify_for_next_turn()
        for player in players_to_notify:
            await self._notify_for_next_turn(player)

    async def _notify_for_next_turn(self, player: User) -> None:
        if player.name not in self.connection_manager.get_registered_user_names():
            for ws in self.connection_manager.get_all_websockets():
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Player {player.name} has disconnected.",
                        }
                    )
                )
            return

        websocket: WebSocket | None = self.connection_manager.get_websocket(player.name)
        if not websocket:
            return

        await websocket.send_text(
            json.dumps(
                {
                    "type": "your_turn",
                    "message": "New round! Make your guess!",
                    "next_player": player.name,
                    "song_list": [song.serialize() for song in player.song_list],
                }
            )
        )

    def _terminate_process(self) -> None:
        """Terminate the process gracefully."""
        os.kill(os.getpid(), signal.SIGINT)

    async def _broadcast_guess_to_other_players(
        self, current_player: str, message: str, result: dict[str, str]
    ) -> None:
        for name, websocket in self.connection_manager.user_connections.items():
            if name != current_player and websocket is not None:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "other_player_guess",
                            "player": current_player,
                            "result": result["result"],
                            "message": message,
                            "next_player": result["next_player"],
                        }
                    )
                )

    async def _broadcast_game_over(self, winner: str) -> None:
        for ws in self.connection_manager.get_all_websockets():
            await ws.send_text(
                json.dumps(
                    {
                        "type": "game_over",
                        "winner": winner,
                        "message": f"{winner} has won the game!",
                    }
                )
            )
        print("Game over, shutting down server...")
