"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from game.errors import GameAlreadyRunningError, MusicPlaybackError
from game.game_logic import GameLogic
from game.messages import MessageType, game_over_message, your_turn_message
from game.user import User
from music_service.error import MusicServiceError
from music_service.selection import MUSIC_SERVICES, MusicServiceType
from server.errors import (
    PlayersNotConnectedError,
    SessionAlreadyExistsError,
    UserAlreadyRegisteredError,
    UserNotRegisteredError,
)
from server.game_sessions import GameSession, game_session_manager
from server.names import (
    USER_NAME_MAX_LENGTH,
    GameId,
    TargetSongCount,
    UserName,
    is_valid_name,
)
from server.spotify_login import router as spotify_auth_router
from server.websocket_handler import WebSocketGameHandler, send_ws_message

logger = logging.getLogger(__name__)

DOMAIN_ERROR_STATUS_CODES: dict[type[Exception], int] = {
    GameAlreadyRunningError: 409,
    MusicPlaybackError: 500,
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


ClientMessageHandler = Callable[
    [WebSocket, str, dict[str, Any], WebSocketGameHandler, GameLogic],
    Awaitable[None],
]


async def _handle_guess_message(
    websocket: WebSocket,
    username: str,
    data: dict[str, Any],
    handler: WebSocketGameHandler,
    game: GameLogic,
) -> None:
    index = data.get("index")
    if not isinstance(index, int) or isinstance(index, bool):
        await send_ws_message(
            websocket, MessageType.ERROR, "Guess index must be an integer."
        )
        return
    await handler.handle_guess(websocket, username, index, game)


async def _handle_ping_message(
    _websocket: WebSocket,
    username: str,
    _data: dict[str, Any],
    _handler: WebSocketGameHandler,
    _game: GameLogic,
) -> None:
    logger.debug("Received ping from %s", username)


CLIENT_MESSAGE_HANDLERS: dict[str, ClientMessageHandler] = {
    "guess": _handle_guess_message,
    "ping": _handle_ping_message,
}


def _disconnected_member_names(session: GameSession) -> list[str]:
    return [
        user.name
        for user in session.game_logic.users
        if session.connection_manager.get_websocket(user.name) is None
    ]


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

        for error_type in DOMAIN_ERROR_STATUS_CODES:
            app.add_exception_handler(error_type, self._domain_error_response)

        return app

    @staticmethod
    async def _domain_error_response(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=DOMAIN_ERROR_STATUS_CODES[type(exc)],
            content={"detail": str(exc)},
        )

    async def _create_game_session(self, req: CreateGameRequest) -> JSONResponse:
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
        joinable_session_ids = [
            session_id
            for session_id, session in game_session_manager.sessions.items()
            if session.game_logic.winner is None
            and (not session.game_logic.running or _disconnected_member_names(session))
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
        if session.game_logic.winner is not None:
            raise HTTPException(
                status_code=409, detail=f"Game session {game_id} is already over."
            )
        if session.game_logic.running:
            self._check_can_rejoin(session, user_name)
            return JSONResponse(
                content={"message": f"User {user_name} can re-join game {game_id}."}
            )

        session.connection_manager.register_user(user_name)

        number_of_users = len(session.connection_manager.get_registered_user_names())
        user_names_string = ", ".join(
            session.connection_manager.get_registered_user_names()
        )
        player_joined_message = {
            "type": MessageType.PLAYER_JOINED,
            "message": (
                f"{user_name} joined the game! "
                f"There are now {number_of_users} players: "
                f"{user_names_string}."
            ),
            "user_name": user_name,
        }

        await session.connection_manager.broadcast(player_joined_message)

        return JSONResponse(
            content={"message": f"User {user_name} joined game {game_id}."}
        )

    @staticmethod
    def _check_can_rejoin(session: GameSession, user_name: str) -> None:
        """Raise unless the name is a member of the running game and not connected."""
        game_id = session.game_id
        joinable_user_names = ", ".join(_disconnected_member_names(session))
        if not session.game_logic.get_user(user_name):
            raise HTTPException(
                status_code=409,
                detail=f"User '{user_name}' is not member in game session "
                f"{game_id}. Only one of the following users can be connected: "
                f"{joinable_user_names}.",
            )
        if session.connection_manager.get_websocket(user_name) is not None:
            raise HTTPException(
                status_code=409,
                detail=f"User '{user_name}' is already connected to "
                f"game session {game_id}. "
                f"Only one of the following users can be connected: "
                f"{joinable_user_names}.",
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

        for player in game.round.get_players_to_notify_for_next_turn():
            ws = connection_manager.get_websocket(player.name)
            if ws is None:
                continue
            await ws.send_text(json.dumps(your_turn_message(player)))

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

        handler = WebSocketGameHandler(game_session.connection_manager)
        if not game.running:
            await handler.handle_connection(websocket, username)
        elif not await self._rejoin(websocket, username, game_session, handler):
            return

        try:
            while True:
                raw_data = await websocket.receive_text()
                await self._handle_message(
                    websocket, username, raw_data, handler, game_session.game_logic
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
        connection_manager = game_session.connection_manager
        member = game_session.game_logic.get_user(username)
        if member is None or connection_manager.get_websocket(username) is not None:
            reason = (
                f"{username} is not a member of this game."
                if member is None
                else f"{username} is already connected."
            )
            await send_ws_message(websocket, MessageType.ERROR, reason)
            await websocket.close(code=1008, reason=reason)
            return False

        await handler.handle_connection(websocket, username)
        member.is_active = True

        user_names = connection_manager.get_registered_user_names()
        player_rejoined_message = {
            "type": MessageType.PLAYER_REJOINED,
            "message": (
                f"{username} re-joined the game! "
                f"There are now {len(user_names)} players: {', '.join(user_names)}."
            ),
            "song_list": [song.serialize() for song in member.song_list],
            "user_name": username,
        }
        if game_session.game_logic.owes_guess(username):
            await websocket.send_text(json.dumps(your_turn_message(member)))
            await connection_manager.broadcast(
                player_rejoined_message, exclude=username
            )
        else:
            await connection_manager.broadcast(player_rejoined_message)
        return True

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
        await client_handler(websocket, username, data, handler, game)

    async def handle_disconnection(
        self, username: str, game_session: GameSession
    ) -> None:
        """Handle user disconnection from the game session."""
        connection_manager = game_session.connection_manager

        connection_manager.unregister_user(username)
        game = game_session.game_logic
        round_advanced = game.running and game.round.player_left(username)

        await connection_manager.broadcast(
            {
                "type": MessageType.USER_DISCONNECTED,
                "message": f"{username} disconnected. "
                f"{username} can try to re-join the game.",
            },
        )
        if round_advanced:
            await WebSocketGameHandler(connection_manager).notify_next_round(game)

        game_id = game_session.game_id
        if not connection_manager.user_connections:
            game_session_manager.remove_game_session(game_id)
            logger.info("Removed empty game session %s", game_id)
