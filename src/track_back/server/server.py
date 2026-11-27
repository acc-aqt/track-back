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

from track_back import __version__
from track_back.game.errors import GameAlreadyRunningError, MusicPlaybackError
from track_back.game.game_logic import GameLogic
from track_back.game.messages import (
    GUESS_REQUEST_TEXT,
    NEW_ROUND_TEXT,
    MessageType,
    game_over_message,
    guess_request_message,
    player_joined_message,
    player_rejoined_message,
)
from track_back.game.player import Player
from track_back.music_service.covers import COVER_URL_PREFIX, cover_store
from track_back.music_service.error import MusicServiceError
from track_back.music_service.selection import (
    MUSIC_SERVICES,
    MusicServiceType,
    available_music_services,
)
from track_back.server import network
from track_back.server.errors import (
    AlreadyConnectedError,
    NotAPlayerError,
    PlayerAlreadyRegisteredError,
    PlayerNotRegisteredError,
    PlayersNotConnectedError,
    SessionAlreadyExistsError,
)
from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.names import (
    USERNAME_MAX_LENGTH,
    SessionName,
    TargetSongCount,
    Username,
    is_valid_name,
)
from track_back.server.spotify_login import router as spotify_auth_router
from track_back.server.websocket_handler import (
    WebSocketGameHandler,
    notify_players_owing_guess,
    send_ws_message,
)

logger = logging.getLogger(__name__)

WEB_UI_DIR = files("track_back") / "web_ui"

DOMAIN_ERROR_STATUS_CODES: dict[type[Exception], int] = {
    AlreadyConnectedError: 409,
    GameAlreadyRunningError: 409,
    MusicPlaybackError: 500,
    NotAPlayerError: 409,
    PlayersNotConnectedError: 409,
    SessionAlreadyExistsError: 409,
    PlayerAlreadyRegisteredError: 409,
    PlayerNotRegisteredError: 404,
}


class CreateGameRequest(BaseModel):
    """Request model for creating a game session."""

    game_id: SessionName
    target_song_count: TargetSongCount
    music_service_type: MusicServiceType | None = None


class JoinGameRequest(BaseModel):
    """Request model for joining a game session."""

    game_id: str
    user_name: Username


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


def startup_hint(port: int, *, use_ssl: bool, lan_addresses: list[str]) -> str:
    """Tell the host which URLs open the Web UI.

    Parameters
    ----------
    port : int
        The port the server listens on.
    use_ssl : bool
        Whether the server serves HTTPS.
    lan_addresses : list[str]
        The addresses other devices can reach this machine on.

    Returns
    -------
    str
        One sentence naming the ``localhost`` URL and one URL per LAN address.
    """
    scheme = "https" if use_ssl else "http"
    hint = f"Open {scheme}://localhost:{port} on this machine"
    if not lan_addresses:
        return f"{hint}."
    lan_urls = " or ".join(f"{scheme}://{address}:{port}" for address in lan_addresses)
    return f"{hint}, or {lan_urls} on other devices."


class Server:
    """Encapsulates the FastAPI application.

    Parameters
    ----------
    music_service : MusicServiceType
        The Music Service chosen by the Server Operator. Game Sessions use it
        unless the Host picks another available one.
    """

    def __init__(self, music_service: MusicServiceType) -> None:
        self.music_service = music_service
        self.available_music_services = available_music_services(music_service)
        self.app = self.create_app()

    def run(self, port: int) -> None:
        """Start the Uvicorn server."""
        ssl_keyfile = os.getenv("SSL_KEYFILE")
        ssl_certfile = os.getenv("SSL_CERTFILE")

        use_ssl = bool(ssl_keyfile and ssl_certfile)
        lan_addresses = network.lan_ipv4_addresses_or_empty()
        print(startup_hint(port, use_ssl=use_ssl, lan_addresses=lan_addresses))

        if use_ssl:
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
        app = FastAPI(title="TrackBack", version=__version__)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.post("/create")(self._create_game_session)
        app.get("/list-sessions")(self._list_joinable_game_sessions)
        app.get(
            COVER_URL_PREFIX + "{cover_id}",
            response_class=Response,
            responses={
                200: {"content": {"image/jpeg": {}}},
                404: {"description": "Unknown cover."},
            },
        )(self._get_cover)
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
        session_name = req.game_id
        target_song_count = req.target_song_count

        music_service_type = req.music_service_type or self.music_service
        if music_service_type not in self.available_music_services:
            available = ", ".join(self.available_music_services)
            raise HTTPException(
                status_code=400,
                detail=f"Music Service {music_service_type} is not available on "
                f"this server. Available: {available}.",
            )

        try:
            music_service = MUSIC_SERVICES[music_service_type]()
        except MusicServiceError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        game = GameLogic(
            target_song_count=target_song_count, music_service=music_service
        )
        game_session_manager.add_session(session_name, game)

        return JSONResponse(
            status_code=201,
            content={"message": f"Game session {session_name} created."},
        )

    async def _list_joinable_game_sessions(self) -> JSONResponse:
        game_session_manager.remove_expired_sessions()
        joinable_session_names = [
            session_name
            for session_name, session in game_session_manager.sessions.items()
            if session.game_logic.winner is None
            and (
                not session.game_logic.running
                or session.game_logic.has_disconnected_players()
            )
        ]
        return JSONResponse(content={"sessions": joinable_session_names})

    @staticmethod
    async def _get_cover(cover_id: str) -> Response:
        image = cover_store.get(cover_id)
        if image is None:
            raise HTTPException(status_code=404, detail="Unknown cover.")
        return Response(content=image, media_type="image/jpeg")

    async def _join_game_session(self, req: JoinGameRequest) -> JSONResponse:
        game_session_manager.remove_expired_sessions()
        session_name = req.game_id
        user_name = req.user_name
        session = game_session_manager.get_game_session(session_name)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {session_name} not found."
            )
        if session.game_logic.winner is not None:
            raise HTTPException(
                status_code=409, detail=f"Game session {session_name} is already over."
            )
        if session.game_logic.running:
            session.check_can_rejoin(user_name)
            return JSONResponse(
                content={
                    "message": f"Player {user_name} can rejoin game session {session_name}."
                }
            )

        connection_manager = session.connection_manager
        connection_manager.register_player(user_name)
        await connection_manager.broadcast(
            player_joined_message(
                user_name, connection_manager.get_registered_player_names()
            )
        )

        return JSONResponse(
            content={
                "message": f"Player {user_name} joined game session {session_name}."
            }
        )

    async def _start_game_session(self, req: StartGameRequest) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        session_name = req.game_id
        session = game_session_manager.get_game_session(session_name)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {session_name} not found."
            )

        game = session.game_logic
        if game.running:
            raise GameAlreadyRunningError(session_name)

        connection_manager = session.connection_manager

        if len(connection_manager.get_registered_player_names()) < 1:
            raise HTTPException(
                status_code=400, detail="Not enough players to start the game."
            )

        if unconnected := connection_manager.get_unconnected_player_names():
            raise PlayersNotConnectedError(unconnected)

        player_names = connection_manager.get_registered_player_names()
        players = [Player(name=user_name) for user_name in player_names]

        game.start_game(players)
        await notify_players_owing_guess(connection_manager, game, GUESS_REQUEST_TEXT)

        return JSONResponse(
            content={"message": f"Game session {session_name} started."}
        )

    async def _websocket_endpoint(
        self, websocket: WebSocket, game_id: str, username: str
    ) -> None:
        await websocket.accept()
        if not is_valid_name(username, USERNAME_MAX_LENGTH):
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
        """Put a player back into the running game; reject anyone else."""
        try:
            player = game_session.check_can_rejoin(username)
        except (NotAPlayerError, AlreadyConnectedError) as e:
            await send_ws_message(websocket, MessageType.ERROR, str(e))
            await websocket.close(code=1008)
            return False

        await handler.handle_connection(websocket, username)

        connection_manager = game_session.connection_manager
        rejoined = player_rejoined_message(
            player, connection_manager.get_registered_player_names()
        )
        if game_session.game_logic.owes_guess(username):
            await websocket.send_text(json.dumps(guess_request_message(player)))
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
        """Handle player disconnection from the game session."""
        connection_manager = game_session.connection_manager
        round_advanced = game_session.disconnect(username)

        await connection_manager.broadcast(
            {
                "type": MessageType.PLAYER_DISCONNECTED,
                "message": f"{username} disconnected. "
                f"{username} can try to re-join the game.",
            },
        )
        if round_advanced:
            await notify_players_owing_guess(
                connection_manager, game_session.game_logic, NEW_ROUND_TEXT
            )

        session_name = game_session.session_name
        if connection_manager.player_connections:
            return
        if game_session.game_logic.running:
            game_session_manager.mark_empty(game_session)
            logger.info("Game session %s is empty; keeping it for rejoin", session_name)
        else:
            game_session_manager.remove_game_session(session_name)
            logger.info("Removed empty game session %s", session_name)
