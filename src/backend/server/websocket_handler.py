import json
import os
import signal

from fastapi import WebSocket

from backend.game.user import User


class WebSocketGameHandler:
    def __init__(self, ctx):
        self.ctx = ctx  # GameContext with game, users, sockets, etc.

    async def handle_connection(self, websocket: WebSocket, username: str):
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

    async def handle_guess(self, websocket: WebSocket, username: str, index: int):
        if self.ctx.game is None:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "⚠️ Game has not started yet."})
            )
            return

        result = self.ctx.game.process_turn(username, index)

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

        # 🏁 Game over?
        if result.get("game_over"):
            await self.broadcast_game_over(result["winner"])
            os.kill(os.getpid(), signal.SIGINT)
            return

        # 🔄 Notify others
        await self.broadcast_turn_result(current_player=username, result=result)

        # 🎮 Tell next player
        await self.notify_next_player(
            next_player=result["next_player"], next_song=result["next_song"]
        )

    async def broadcast_turn_result(self, current_player: str, result: dict):
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

    async def notify_next_player(self, next_player: str, next_song: str):
        if next_player in self.ctx.connected_users:
            next_ws = self.ctx.connected_users[next_player]
            player = self.ctx.registered_users[next_player]
            await next_ws.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "next_player": next_player,
                        "next_song": next_song,
                        "song_list": self.ctx.game._serialize_song_list(player.song_list),
                    }
                )
            )

    async def broadcast_game_over(self, winner: str):
        for _, ws in self.ctx.connected_users.items():
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
