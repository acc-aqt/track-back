"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from game.game_logic import GameLogic
from game.user import User
from music_service.factory import MusicServiceFactory
from music_service.spotify import router as spotify_auth_router
from server.game_sessions import GameSession, game_session_manager
from server.websocket_handler import WebSocketGameHandler


class CreateGameRequest(BaseModel):
    """Request model for creating a game session."""

    game_id: str
    target_song_count: int
    music_service_type: str


class JoinGameRequest(BaseModel):
    """Request model for joining a game session."""

    game_id: str
    user_name: str


class StartGameRequest(BaseModel):
    """Request model for starting a game session."""

    game_id: str


class Server:
    """Encapsulates the FastAPI application."""

    def __init__(self) -> None:
        self.app = self.create_app()

    def run(self, port: int) -> None:
        """Start the Uvicorn server."""
        ssl_keyfile = os.getenv("SSL_KEYFILE")
        ssl_certfile = os.getenv("SSL_CERTFILE")

        if ssl_keyfile and ssl_certfile:
            logging.info("Running server with SSL.")
            uvicorn.run(
                self.app,
                host="0.0.0.0",  # noqa: S104
                port=port,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
            )
        else:
            logging.info("Running server without SSL.")
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

        app.post("/create")(self._create_game_session)
        app.get("/list-sessions")(self._list_joinable_game_sessions)
        app.post("/join")(self._join_game_session)
        app.post("/start")(self._start_game_session)
        app.websocket("/ws/{game_id}/{username}")(self._websocket_endpoint)
        app.include_router(spotify_auth_router)

        return app

    async def _create_game_session(self, req: CreateGameRequest) -> JSONResponse:
        game_id = req.game_id
        target_song_count = req.target_song_count

        music_service_type = req.music_service_type
        music_service = MusicServiceFactory.create_music_service(music_service_type)

        game = GameLogic(
            target_song_count=target_song_count, music_service=music_service
        )
        game_session_manager.add_game(game_id, game)

        return JSONResponse(
            status_code=201, content={"message": f"Game session {game_id} created."}
        )

    async def _list_joinable_game_sessions(self) -> JSONResponse:
        joinable_session_ids = [
            session_id
            for session_id, session in game_session_manager.sessions.items()
            if not session.game_logic.running
            or any(user.is_active is False for user in session.game_logic.users)
        ]
        return JSONResponse(content={"sessions": joinable_session_ids})

    async def _join_game_session(self, req: JoinGameRequest) -> JSONResponse:
        game_id = req.game_id
        user_name = req.user_name
        session = game_session_manager.get_game_session(game_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {game_id} not found."
            )
        if session.game_logic.running:
            user_to_reconnect = session.game_logic.get_user(user_name)
            joinable_user_names = ", ".join(
                [user.name for user in session.game_logic.users if not user.is_active]
            )
            if not user_to_reconnect:
                raise HTTPException(
                    status_code=409,
                    detail=f"User '{user_name}' is not member in game session "
                    f"{game_id}. Only one of the following users can be connected: "
                    f"{joinable_user_names}.",
                )
            if user_to_reconnect.is_active:
                raise HTTPException(
                    status_code=409,
                    detail=f"User '{user_name}' is already connected to "
                    f"game session {game_id}. "
                    f"Only one of the following users can be connected: "
                    f"{joinable_user_names}.",
                )
            user_to_reconnect.is_active = True
            session.connection_manager.register_user(user_name)

            number_of_users = len(
                session.connection_manager.get_registered_user_names()
            )
            user_names_string = ", ".join(
                session.connection_manager.get_registered_user_names()
            )

            player_rejoined_message = {
                "type": "player_rejoined",
                "message": (
                    f"{user_name} re-joined the game! "
                    f"There are now {number_of_users} players: "
                    f"{user_names_string}."
                ),
                "song_list": [song.serialize() for song in user_to_reconnect.song_list],
                "user_name": user_name,
                "next_player": user_name,
            }

            await self._broadcast_to_all_connected_users(
                session, player_rejoined_message
            )
            return JSONResponse(
                content={"message": f"User {user_name} re-joined game {game_id}."}
            )

        session.connection_manager.register_user(user_name)

        number_of_users = len(session.connection_manager.get_registered_user_names())
        user_names_string = ", ".join(
            session.connection_manager.get_registered_user_names()
        )
        player_joined_message = {
            "type": "player_joined",
            "message": (
                f"{user_name} joined the game! "
                f"There are now {number_of_users} players: "
                f"{user_names_string}."
            ),
            "user_name": user_name,
        }

        await self._broadcast_to_all_connected_users(session, player_joined_message)

        return JSONResponse(
            content={"message": f"User {user_name} joined game {game_id}."}
        )

    async def _broadcast_to_all_connected_users(
        self, session: GameSession, message: dict[str, Any]
    ) -> None:
        """Broadcast a message to all connected users in the game session."""
        for ws in session.connection_manager.get_all_websockets():
            if ws.client_state.name != "CONNECTED":
                continue
            await ws.send_text(json.dumps(message))

    async def _start_game_session(self, req: StartGameRequest) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        game_id = req.game_id
        session = game_session_manager.get_game_session(game_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {game_id} not found."
            )

        connection_manager = session.connection_manager

        if len(connection_manager.get_registered_user_names()) < 1:
            raise HTTPException(
                status_code=400, detail="Not enough players to start the game."
            )

        user_names = connection_manager.get_registered_user_names()
        users = [User(name=user_name) for user_name in user_names]

        game = session.game_logic

        game.start_game(users)

        players_to_notify = game.strategy.get_players_to_notify_for_next_turn()

        for player in players_to_notify:
            ws = connection_manager.get_websocket(player.name)
            if not ws:
                raise HTTPException(
                    status_code=409,
                    detail=f"{player.name} is not connected via WebSocket.",
                )

            await ws.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "message": "It's your turn!",
                        "next_player": player.name,
                        "song_list": [song.serialize() for song in player.song_list],
                    }
                )
            )

        return JSONResponse(
            status_code=200,
            content={
                "type": "game_start",
                "message": f"Game {game_id} started.",
            },
        )

    async def _websocket_endpoint(
        self, websocket: WebSocket, game_id: str, username: str
    ) -> None:
        await websocket.accept()
        game_session = game_session_manager.get_game_session(game_id)
        if not game_session:
            await websocket.close()
            logging.error("Game session %s not found.", game_id)
            return

        connection_manager = game_session.connection_manager
        if connection_manager.first_player is None:
            connection_manager.first_player = username
            logging.info("First player: %s", connection_manager.first_player)

        handler = WebSocketGameHandler(connection_manager)
        await handler.handle_connection(websocket, username)

        player = game_session.game_logic.get_user(username)

        if (
            game_session.game_logic.running
            and player
            in game_session.game_logic.strategy.get_players_to_notify_for_next_turn()
        ):
            if ws := connection_manager.get_websocket(username):
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "your_turn",
                            "message": "It's your turn!",
                            "next_player": username,
                            "song_list": [
                                song.serialize() for song in player.song_list
                            ],
                        }
                    )
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"{username} is not connected via WebSocket.",
                )

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                game = game_session.game_logic

                if data.get("type") == "guess":
                    index = data.get("index")
                    await handler.handle_guess(websocket, username, index, game)
                else:
                    await websocket.send_text("Unknown message type.")

                if not game.running:
                    game_session_manager.remove_game_session(game_id)

        except WebSocketDisconnect:
            await self.handle_disconnection(username, game_session)

    async def handle_disconnection(
        self, username: str, game_session: GameSession
    ) -> None:
        """Handle user disconnection from the game session."""
        connection_manager = game_session.connection_manager

        connection_manager.unregister_user(username)

        if inactive_user := game_session.game_logic.get_user(username):
            inactive_user.is_active = False

        await self._broadcast_to_all_connected_users(
            game_session,
            {
                "type": "user_disconnected",
                "message": f"{username} disconnected. "
                f"{username} can try to re-join the game.",
            },
        )

        game_id = game_session.game_id
        if not connection_manager.user_connections:
            game_session_manager.remove_game_session(game_id)
            logging.info("Removed empty game session %s", game_id)
