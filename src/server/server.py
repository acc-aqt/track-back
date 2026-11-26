"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
from typing import Annotated, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from game.game_logic import GameLogic
from game.user import User
from music_service.error import MusicServiceError
from music_service.factory import MusicServiceFactory
from music_service.spotify import router as spotify_auth_router
from server.game_sessions import GameSession, game_session_manager
from server.names import (
    GAME_ID_MAX_LENGTH,
    NAME_PATTERN,
    USER_NAME_MAX_LENGTH,
    is_valid_name,
)
from server.websocket_handler import WebSocketGameHandler, send_ws_message

logger = logging.getLogger(__name__)

UserName = Annotated[str, Field(max_length=USER_NAME_MAX_LENGTH, pattern=NAME_PATTERN)]
GameId = Annotated[str, Field(max_length=GAME_ID_MAX_LENGTH, pattern=NAME_PATTERN)]


class CreateGameRequest(BaseModel):
    """Request model for creating a game session."""

    game_id: GameId
    target_song_count: int
    music_service_type: str


class JoinGameRequest(BaseModel):
    """Request model for joining a game session."""

    game_id: str
    user_name: UserName


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
            logger.info("Running server with SSL.")
            uvicorn.run(
                self.app,
                host="0.0.0.0",  # noqa: S104
                port=port,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
            )
        else:
            logger.info("Running server without SSL.")
            uvicorn.run(self.app, host="0.0.0.0", port=port)  # noqa: S104

    def create_app(self) -> FastAPI:
        """Initialize and configure the FastAPI app with middleware and routes."""
        app = FastAPI(title="TrackBack", version="0.1.0")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
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
        try:
            music_service = MusicServiceFactory.create_music_service(music_service_type)
        except MusicServiceError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

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

        players_to_notify = game.round.get_players_to_notify_for_next_turn()

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
        if not is_valid_name(username, USER_NAME_MAX_LENGTH):
            await websocket.close(code=1008, reason="Invalid user name.")
            return
        game_session = game_session_manager.get_game_session(game_id)
        if not game_session:
            await websocket.close()
            logger.error("Game session %s not found.", game_id)
            return

        connection_manager = game_session.connection_manager
        handler = WebSocketGameHandler(connection_manager)
        await handler.handle_connection(websocket, username)

        player = game_session.game_logic.get_user(username)

        if (
            player
            and game_session.game_logic.running
            and player
            in game_session.game_logic.round.get_players_to_notify_for_next_turn()
        ):
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "message": "It's your turn!",
                        "next_player": username,
                        "song_list": [song.serialize() for song in player.song_list],
                    }
                )
            )

        try:
            while True:
                raw_data = await websocket.receive_text()
                await self._handle_message(
                    websocket, username, raw_data, handler, game_session.game_logic
                )
                if game_session.game_logic.winner is not None:
                    game_session_manager.remove_game_session(game_id)

        except WebSocketDisconnect:
            await self.handle_disconnection(username, game_session)

    @staticmethod
    async def _handle_message(
        websocket: WebSocket,
        username: str,
        raw_data: str,
        handler: WebSocketGameHandler,
        game: GameLogic,
    ) -> None:
        """Parse one client message and dispatch it."""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            await send_ws_message(websocket, "error", "Invalid JSON.")
            return
        if not isinstance(data, dict):
            await send_ws_message(websocket, "error", "Expected an object.")
            return

        if data.get("type") == "guess":
            index = data.get("index")
            if not isinstance(index, int) or isinstance(index, bool):
                await send_ws_message(
                    websocket, "error", "Guess index must be an integer."
                )
                return
            await handler.handle_guess(websocket, username, index, game)
        elif data.get("type") == "ping":
            logger.debug("Received ping from %s", username)
        else:
            await send_ws_message(websocket, "error", "Unknown message type.")

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
            logger.info("Removed empty game session %s", game_id)
