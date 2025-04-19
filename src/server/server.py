"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
import signal

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from game.track_back_game import TrackBackGame
from game.user import User
from game.game_modes import GameMode
from server.game_context import GameContext
from server.websocket_handler import WebSocketGameHandler


class Server:
    """Encapsulates the FastAPI application."""

    def __init__(self, game_context: GameContext, port: int) -> None:
        self.game_context = game_context
        self.port = port
        self.app = self.create_app()

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

    async def _shutdown(self) -> JSONResponse:
        """Gracefully shut down the server process."""
        logging.info("🛑 Shutdown requested via web UI")
        os.kill(os.getpid(), signal.SIGINT)
        return JSONResponse(status_code=200, content={"message": "Server shutdown initiated."})

    async def _register(self, user_name: str) -> JSONResponse:
        """Register a new user for the game via REST POST."""
        if user_name in self.game_context.registered_users:
            raise HTTPException(status_code=409, detail=f"User '{user_name}' already registered")

        self.game_context.registered_users[user_name] = User(name=user_name)

        return JSONResponse(
            status_code=201,
            content={
                "message": "User '{user_name}' registered successfully.",
                "user": user_name,
            },
        )

    async def _start_game(self) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        if self.game_context.game is not None:
            raise HTTPException(status_code=400, detail="Game already started.")

        if len(self.game_context.registered_users) < 1:
            raise HTTPException(status_code=400, detail="Not enough players to start the game.")
        users = list(self.game_context.registered_users.values())
        self.game_context.game = TrackBackGame(
            users,
            self.game_context.target_song_count,
            self.game_context.music_service,
            self.game_context.game_mode,
        )
        self.game_context.game.start_game()

        if self.game_context.game_mode == GameMode.SEQUENTIAL:

            players_to_notify = [self.game_context.game.get_current_player()]
        elif self.game_context.game_mode == GameMode.SIMULTANEOUS:
            players_to_notify = self.game_context.game.users
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid game mode. Only SEQUENTIAL and SIMULTANEOUS are supported.",
            )

        print("Players to notify:")
        print(players_to_notify)

        for player in players_to_notify:

            ws = self.game_context.connected_users.get(player.name)
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
                "message": "Game started!",
                "first_player": player.name,
            },
        )

    async def _websocket_endpoint(self, websocket: WebSocket, username: str) -> None:
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
