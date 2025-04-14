"""Contains the WebSocket handler for the game server."""

import json
import os
import signal

from fastapi import WebSocket

from backend.game.user import User

from .game_context import GameContext


class WebSocketGameHandler:
    """WebSocket handler for managing game connections and interactions."""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx  # GameContext with game, users, sockets, etc.

    async def handle_connection(self, websocket: WebSocket, username: str) -> None:
        """Handle a new WebSocket connection for a player."""
        if username in self.ctx.registered_users:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "welcome",
                        "message": f"✅ Welcome back, {username}!",
                    }
                )
            )
        else:
            self.ctx.registered_users[username] = User(name=username)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "welcome",
                        "message": f"✅ Welcome, {username}! You're connected.",
                        "first_player": username == self.ctx.first_player,
                    }
                )
            )
        self.ctx.connected_users[username] = websocket

    async def handle_guess(
        self, websocket: WebSocket, username: str, index: int
    ) -> None:
        """Handle a guess from a player."""
        if self.ctx.game is None:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "⚠️ Game has not started yet."})
            )
            return

        result = self.ctx.game.handle_player_turn(username, index)

        # 🎯 Send result to the player who guessed
        await websocket.send_text(
            json.dumps(
                {
                    "type": "guess_result",
                    "player": username,
                    "result": result["result"],
                    "message": result["message"],
                    "song_list": result["song_list"],
                }
            )
        )

        if result.get("game_over"):
            await self._broadcast_game_over(result["winner"])
            os.kill(os.getpid(), signal.SIGINT)
            return
        await self._broadcast_turn_result(current_player=username, result=result)

        await self._notify_next_player(next_player=result["next_player"])

    async def _broadcast_turn_result(
        self, current_player: str, result: dict[str, str]
    ) -> None:
        for name, ws in self.ctx.connected_users.items():
            if name != current_player:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "turn_result",
                            "player": current_player,
                            "result": result["result"],
                            "message": result["message"],
                            "next_player": result["next_player"],
                        }
                    )
                )

    async def _notify_next_player(self, next_player: str) -> None:
        if next_player in self.ctx.connected_users:
            next_ws = self.ctx.connected_users[next_player]
            player = self.ctx.registered_users[next_player]
            serialized_song_list = [song.serialize() for song in player.song_list]
            await next_ws.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "next_player": next_player,
                        "song_list": serialized_song_list,
                    }
                )
            )

    async def _broadcast_game_over(self, winner: str) -> None:
        for ws in self.ctx.connected_users.values():
            await ws.send_text(
                json.dumps(
                    {
                        "type": "game_over",
                        "winner": winner,
                        "message": f"🏆 {winner} has won the game!",
                    }
                )
            )
        print("💥 Game over, shutting down server...")
