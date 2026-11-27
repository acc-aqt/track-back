"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from track_back.game.errors import GameAlreadyRunningError, MusicPlaybackError
from track_back.game.game_logic import GameLogic
from track_back.game.messages import (
    NEW_ROUND_TEXT,
    YOUR_TURN_TEXT,
    MessageType,
    game_over_message,
    player_joined_message,
    player_rejoined_message,
    your_turn_message,
)
from track_back.game.user import User
from track_back.music_service.error import MusicServiceError
from track_back.music_service.selection import MUSIC_SERVICES, MusicServiceType
from track_back.server.errors import (
    AlreadyConnectedError,
    NotAMemberError,
    PlayersNotConnectedError,
    SessionAlreadyExistsError,
    UserAlreadyRegisteredError,
    UserNotRegisteredError,
)
from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.names import (
    USER_NAME_MAX_LENGTH,
    GameId,
    TargetSongCount,
    UserName,
    is_valid_name,
)
from track_back.server.spotify_login import router as spotify_auth_router
from track_back.server.websocket_handler import (
    WebSocketGameHandler,
    notify_players_owed_card,
    send_ws_message,
)

logger = logging.getLogger(__name__)

WEB_UI_DIR = files("track_back") / "web_ui"

DOMAIN_ERROR_STATUS_CODES: dict[type[Exception], int] = {
    AlreadyConnectedError: 409,
    GameAlreadyRunningError: 409,
    MusicPlaybackError: 500,
    NotAMemberError: 409,
    PlayersNotConnectedError: 409,
    SessionAlreadyExistsError: 409,
    UserAlreadyRegisteredError: 409,
    UserNotRegisteredError: 404,
}


class CreateGameRequest(BaseModel):
    """Request model for creating a game session."""

    game_id: GameId
    target_song_count: TargetSongCount
    music_service_type: MusicServiceType


class JoinGameRequest(BaseModel):
    """Request model for joining a game session."""

    game_id: str
    user_name: UserName


class StartGameRequest(BaseModel):
    """Request model for starting a game session."""

    game_id: str


@dataclass(frozen=True)
class ClientMessageContext:
    """The connection a client message arrived on."""

    websocket: WebSocket
    username: str
    handler: WebSocketGameHandler


ClientMessageHandler = Callable[[ClientMessageContext, dict[str, Any]], Awaitable[None]]


async def _handle_guess_message(
    context: ClientMessageContext, data: dict[str, Any]
) -> None:
    index = data.get("index")
    if not isinstance(index, int) or isinstance(index, bool):
        await send_ws_message(
            context.websocket, MessageType.ERROR, "Guess index must be an integer."
        )
        return
    await context.handler.handle_guess(context.websocket, context.username, index)


async def _handle_ping_message(
    context: ClientMessageContext, _data: dict[str, Any]
) -> None:
    logger.debug("Received ping from %s", context.username)


CLIENT_MESSAGE_HANDLERS: dict[str, ClientMessageHandler] = {
    "guess": _handle_guess_message,
    "ping": _handle_ping_message,
}


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
        app.get("/server_config.js", include_in_schema=False)(self._server_config)

        for error_type in DOMAIN_ERROR_STATUS_CODES:
            app.add_exception_handler(error_type, self._domain_error_response)

        app.mount("/", StaticFiles(directory=str(WEB_UI_DIR), html=True), name="web_ui")

        return app

    @staticmethod
    async def _server_config(request: Request) -> Response:
        """Point the bundled Web UI at the origin it was loaded from."""
        config = {"TRACK_BACK_SERVER_URL": str(request.base_url).rstrip("/")}
        return Response(
            content=f"window.TRACK_BACK_CONFIG = {json.dumps(config)};\n",
            media_type="text/javascript",
        )

    @staticmethod
    async def _domain_error_response(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=DOMAIN_ERROR_STATUS_CODES[type(exc)],
            content={"detail": str(exc)},
        )

    async def _create_game_session(self, req: CreateGameRequest) -> JSONResponse:
        game_session_manager.remove_expired_sessions()
        game_id = req.game_id
        target_song_count = req.target_song_count

        try:
            music_service = MUSIC_SERVICES[req.music_service_type]()
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
        game_session_manager.remove_expired_sessions()
        joinable_session_ids = [
            session_id
            for session_id, session in game_session_manager.sessions.items()
            if session.game_logic.winner is None
            and (
                not session.game_logic.running
                or session.game_logic.has_inactive_members()
            )
        ]
        return JSONResponse(content={"sessions": joinable_session_ids})

    async def _join_game_session(self, req: JoinGameRequest) -> JSONResponse:
        game_session_manager.remove_expired_sessions()
        game_id = req.game_id
        user_name = req.user_name
        session = game_session_manager.get_game_session(game_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {game_id} not found."
            )
        if session.game_logic.winner is not None:
            raise HTTPException(
                status_code=409, detail=f"Game session {game_id} is already over."
            )
        if session.game_logic.running:
            session.check_can_rejoin(user_name)
            return JSONResponse(
                content={"message": f"User {user_name} can re-join game {game_id}."}
            )

        connection_manager = session.connection_manager
        connection_manager.register_user(user_name)
        await connection_manager.broadcast(
            player_joined_message(
                user_name, connection_manager.get_registered_user_names()
            )
        )

        return JSONResponse(
            content={"message": f"User {user_name} joined game {game_id}."}
        )

    async def _start_game_session(self, req: StartGameRequest) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        game_id = req.game_id
        session = game_session_manager.get_game_session(game_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {game_id} not found."
            )

        game = session.game_logic
        if game.running:
            raise GameAlreadyRunningError(game_id)

        connection_manager = session.connection_manager

        if len(connection_manager.get_registered_user_names()) < 1:
            raise HTTPException(
                status_code=400, detail="Not enough players to start the game."
            )

        if unconnected := connection_manager.get_unconnected_user_names():
            raise PlayersNotConnectedError(unconnected)

        user_names = connection_manager.get_registered_user_names()
        users = [User(name=user_name) for user_name in user_names]

        game.start_game(users)
        await notify_players_owed_card(connection_manager, game, YOUR_TURN_TEXT)

        return JSONResponse(content={"message": f"Game {game_id} started."})

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

        game = game_session.game_logic
        if game.winner is not None:
            await websocket.send_text(json.dumps(game_over_message(game.winner.name)))
            await websocket.close()
            return

        handler = WebSocketGameHandler(game_session)
        if not game.running:
            await handler.handle_connection(websocket, username)
        elif not await self._rejoin(websocket, username, game_session, handler):
            return

        try:
            while True:
                raw_data = await websocket.receive_text()
                await self._handle_message(
                    ClientMessageContext(websocket, username, handler), raw_data
                )

        except WebSocketDisconnect:
            await self.handle_disconnection(username, game_session)

    @staticmethod
    async def _rejoin(
        websocket: WebSocket,
        username: str,
        game_session: GameSession,
        handler: WebSocketGameHandler,
    ) -> bool:
        """Put a member back into the running game; reject anyone else."""
        try:
            member = game_session.check_can_rejoin(username)
        except (NotAMemberError, AlreadyConnectedError) as e:
            await send_ws_message(websocket, MessageType.ERROR, str(e))
            await websocket.close(code=1008)
            return False

        await handler.handle_connection(websocket, username)

        connection_manager = game_session.connection_manager
        rejoined = player_rejoined_message(
            member, connection_manager.get_registered_user_names()
        )
        if game_session.game_logic.owes_guess(username):
            await websocket.send_text(json.dumps(your_turn_message(member)))
            await connection_manager.broadcast(rejoined, exclude=username)
        else:
            await connection_manager.broadcast(rejoined)
        return True

    @staticmethod
    async def _handle_message(context: ClientMessageContext, raw_data: str) -> None:
        """Parse one client message and dispatch it."""
        websocket = context.websocket
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            await send_ws_message(websocket, MessageType.ERROR, "Invalid JSON.")
            return
        if not isinstance(data, dict):
            await send_ws_message(websocket, MessageType.ERROR, "Expected an object.")
            return

        message_type = data.get("type")
        client_handler = (
            CLIENT_MESSAGE_HANDLERS.get(message_type)
            if isinstance(message_type, str)
            else None
        )
        if client_handler is None:
            await send_ws_message(websocket, MessageType.ERROR, "Unknown message type.")
            return
        await client_handler(context, data)

    async def handle_disconnection(
        self, username: str, game_session: GameSession
    ) -> None:
        """Handle user disconnection from the game session."""
        connection_manager = game_session.connection_manager
        round_advanced = game_session.disconnect(username)

        await connection_manager.broadcast(
            {
                "type": MessageType.USER_DISCONNECTED,
                "message": f"{username} disconnected. "
                f"{username} can try to re-join the game.",
            },
        )
        if round_advanced:
            await notify_players_owed_card(
                connection_manager, game_session.game_logic, NEW_ROUND_TEXT
            )

        game_id = game_session.game_id
        if connection_manager.user_connections:
            return
        if game_session.game_logic.running:
            game_session_manager.mark_empty(game_session)
            logger.info("Game session %s is empty; keeping it for rejoin", game_id)
        else:
            game_session_manager.remove_game_session(game_id)
            logger.info("Removed empty game session %s", game_id)
