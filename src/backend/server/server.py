"""Contains the game server class."""

import json
import logging
import os
import signal

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.game.track_back_game import TrackBackGame
from backend.game.user import User
from backend.server.local_ip import get_local_ip
from backend.server.websocket_handler import WebSocketGameHandler

from .game_context import GameContext


class Server:
    """
    Encapsulates the FastAPI application and game lifecycle management.
    The server handles WebSocket connections.
    REST endpoints are used for registration and game management.
    """

    def __init__(self, game_context: GameContext, port: int) -> None:
        self.game_context = game_context
        self.port = port
        self.app = self.create_app()
        self.ip = get_local_ip()
        self.url = f"http://{self.ip}:{self.port}"
        logging.info("\n🌍 Game server running at: %s\n", self.url)

    def run(self) -> None:
        """Start the Uvicorn server."""
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)  # noqa: S104

    def create_app(self) -> FastAPI:
        """Initialize and configure the FastAPI app with middleware and routes."""
        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.state.ctx = self.game_context

        app.post("/shutdown")(self._shutdown)
        app.post("/register")(self._register)
        app.post("/start")(self._start_game)
        app.websocket("/ws/{username}")(self._websocket_endpoint)

        return app

    async def _shutdown(self) -> dict[str, str]:
        """Gracefully shut down the server process."""
        logging.info("🛑 Shutdown requested via web UI")
        os.kill(os.getpid(), signal.SIGINT)
        return {"message": "Server is shutting down..."}

    async def _register(self, user_name: str) -> dict[str, str]:
        """Register a new user for the game via REST POST."""
        if user_name in self.game_context.registered_users:
            return {"error": f"User '{user_name}' already registered"}
        self.game_context.registered_users[user_name] = User(name=user_name)

        return {"message": f"User '{user_name}' registered successfully."}

    async def _start_game(self) -> dict[str, str]:
        """Start the game and notify the first player via WebSocket."""
        if len(self.game_context.registered_users) < 1:
            return {"error": "Not enough players to start the game."}

        users = list(self.game_context.registered_users.values())
        self.game_context.game = TrackBackGame(
            users,
            self.game_context.target_song_count,
            self.game_context.music_service,
        )
        self.game_context.game.start_game()

        first_player = self.game_context.game.get_current_player()

        ws = self.game_context.connected_users.get(first_player.name)
        if not ws:
            return {"error": f"{first_player.name} is not connected via WebSocket."}

        await ws.send_text(
            json.dumps(
                {
                    "type": "your_turn",
                    "message": "🎮 It's your turn!",
                    "next_player": first_player.name,
                    "song_list": [song.serialize() for song in first_player.song_list],
                }
            )
        )

        return {
            "message": "Game started!",
            "first_player": first_player.name,
        }

    async def _websocket_endpoint(self, websocket: WebSocket, username: str) -> None:
        """Handle incoming WebSocket connection for a player."""
        await websocket.accept()
        ctx = websocket.app.state.ctx
        if ctx.first_player is None:
            ctx.first_player = username
            logging.info("📌 First player: %s", ctx.first_player)

        handler = WebSocketGameHandler(ctx)

        await handler.handle_connection(websocket, username)

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                if data.get("type") == "guess":
                    index = data.get("index")
                    await handler.handle_guess(websocket, username, index)
                else:
                    await websocket.send_text("❓ Unknown message type.")
        except WebSocketDisconnect:
            logging.info("User %s disconnected", username)
            ctx.connected_users.pop(username, None)
