"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
import signal

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from game.game_logic import GameLogic
from game.user import User
from music_service.error import MusicServiceError
from server.connection_manager import ConnectionManager
from server.websocket_handler import WebSocketGameHandler


class Server:
    """Encapsulates the FastAPI application."""

    def __init__(self, connection_manager: ConnectionManager, game: GameLogic) -> None:
        self.connection_manager = connection_manager
        self.game = game
        self.app = self.create_app()

    def run(self, port: int) -> None:
        """Start the Uvicorn server."""
        uvicorn.run(self.app, host="0.0.0.0", port=port)  # noqa: S104

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

        app.post("/shutdown")(self._shutdown)
        app.post("/register")(self._register)
        app.post("/start")(self._start_game)
        app.websocket("/ws/{username}")(self._websocket_endpoint)

        return app

    async def _shutdown(self) -> JSONResponse:
        """Gracefully shut down the server process."""
        logging.info("🛑 Shutdown requested via web UI")
        os.kill(os.getpid(), signal.SIGINT)
        return JSONResponse(
            status_code=200, content={"message": "Server shutdown initiated."}
        )

    async def _register(self, user_name: str) -> JSONResponse:
        """Register a new user for the game via REST POST."""
        if user_name in self.connection_manager.registered_users:
            raise HTTPException(
                status_code=409, detail=f"User '{user_name}' already registered"
            )

        self.connection_manager.registered_users[user_name] = User(name=user_name)

        return JSONResponse(
            status_code=201,
            content={
                "message": "User '{user_name}' registered successfully.",
                "user": user_name,
            },
        )

    async def _start_game(self) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        if len(self.connection_manager.registered_users) < 1:
            raise HTTPException(
                status_code=400, detail="Not enough players to start the game."
            )

        try:
            self.game.music_service.start_playback()
        except MusicServiceError as e:
            raise HTTPException(
                status_code=500,
                detail="Failed to play music",
            ) from e

        users = list(self.connection_manager.registered_users.values())

        self.game.start_game(users)

        players_to_notify = self.game.strategy.get_players_to_notify_for_next_turn()
        for player in players_to_notify:
            ws = self.connection_manager.get_websocket(player.name)
            if not ws:
                raise HTTPException(
                    status_code=409,
                    detail=f"{player.name} is not connected via WebSocket.",
                )

            await ws.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "message": "🎮 It's your turn!",
                        "next_player": player.name,
                        "song_list": [song.serialize() for song in player.song_list],
                    }
                )
            )

        return JSONResponse(
            status_code=200,
            content={
                "type": "game_start",
                "message": "Game started successfully.",
            },
        )

    async def _websocket_endpoint(self, websocket: WebSocket, username: str) -> None:
        await websocket.accept()

        connection_manager = self.connection_manager
        if connection_manager.first_player is None:
            connection_manager.first_player = username
            logging.info("📌 First player: %s", connection_manager.first_player)

        handler = WebSocketGameHandler(connection_manager)
        await handler.handle_connection(websocket, username)

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                if data.get("type") == "guess":
                    index = data.get("index")
                    await handler.handle_guess(websocket, username, index, self.game)
                else:
                    await websocket.send_text("❓ Unknown message type.")
        except WebSocketDisconnect:
            logging.info("User %s disconnected", username)
            connection_manager.websockets.pop(username, None)
