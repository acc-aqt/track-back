"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging
import os
import socket
from collections.abc import Awaitable, Callable, Mapping
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
from track_back.music_service.covers import COVER_URL_PREFIX, cover_store
from track_back.music_service.error import MusicServiceError
from track_back.music_service.selection import (
    MUSIC_SERVICES,
    MusicServiceDescription,
    MusicServiceType,
    available_music_services,
)
from track_back.server import config, join_qr, network
from track_back.server.errors import (
    AlreadyConnectedError,
    GameSessionOverError,
    NotAPlayerError,
    NotEnoughPlayersError,
    PlayerAlreadyRegisteredError,
    PlayersNotConnectedError,
    SessionAlreadyExistsError,
)
from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.messages import error_message, game_over_message
from track_back.server.names import (
    USERNAME_MAX_LENGTH,
    SessionName,
    TargetSongCount,
    Username,
    is_valid_name,
)
from track_back.server.spotify_login import router as spotify_auth_router

logger = logging.getLogger(__name__)

WEB_UI_DIR = files("track_back") / "web_ui"

DOMAIN_ERROR_STATUS_CODES: dict[type[Exception], int] = {
    AlreadyConnectedError: 409,
    GameAlreadyRunningError: 409,
    GameSessionOverError: 409,
    MusicPlaybackError: 500,
    NotAPlayerError: 409,
    NotEnoughPlayersError: 400,
    PlayersNotConnectedError: 409,
    SessionAlreadyExistsError: 409,
    PlayerAlreadyRegisteredError: 409,
}


class CreateGameRequest(BaseModel):
    """Request model for creating a game session."""

    game_id: SessionName
    target_song_count: TargetSongCount
    music_service_type: MusicServiceType | None = None


class MusicServicesResponse(BaseModel):
    """The Music Services a Host can create a Game Session with."""

    default: MusicServiceType
    available: list[MusicServiceType]


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
    session: GameSession


ClientMessageHandler = Callable[[ClientMessageContext, dict[str, Any]], Awaitable[None]]


async def _send(websocket: WebSocket, message: dict[str, Any]) -> None:
    await websocket.send_text(json.dumps(message))


async def _handle_guess_message(
    context: ClientMessageContext, data: dict[str, Any]
) -> None:
    index = data.get("index")
    if not isinstance(index, int) or isinstance(index, bool):
        await _send(context.websocket, error_message("Guess index must be an integer."))
        return
    session = context.session
    try:
        outgoing = session.guess(context.username, index)
    except MusicServiceError as e:
        await _send(context.websocket, error_message(str(e)))
        return
    await session.connection_manager.deliver(outgoing)


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
    hint = f"Open {base_url('localhost', port, use_ssl=use_ssl)} on this machine"
    if not lan_addresses:
        return f"{hint}."
    lan_urls = " or ".join(
        base_url(address, port, use_ssl=use_ssl) for address in lan_addresses
    )
    return f"{hint}, or {lan_urls} on other devices."


def base_url(host: str, port: int, *, use_ssl: bool) -> str:
    """Build the server's URL on ``host``, without a trailing slash."""
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


def _ssl_files() -> tuple[str, str] | None:
    keyfile = os.getenv("SSL_KEYFILE")
    certfile = os.getenv("SSL_CERTFILE")
    if keyfile and certfile:
        return keyfile, certfile
    return None


def uses_ssl() -> bool:
    """Tell whether the SSL config asks the server to serve HTTPS.

    Returns
    -------
    bool
        True when both ``SSL_KEYFILE`` and ``SSL_CERTFILE`` are set.
    """
    return _ssl_files() is not None


class _ReadyNotifyingServer(uvicorn.Server):
    """Uvicorn server that runs callbacks once it accepts connections."""

    def __init__(
        self, config: uvicorn.Config, ready_callbacks: list[Callable[[], None]]
    ) -> None:
        super().__init__(config)
        self._ready_callbacks = ready_callbacks

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if not self.started:
            return
        for callback in self._ready_callbacks:
            callback()


class Server:
    """Encapsulates the FastAPI application.

    Parameters
    ----------
    music_service : MusicServiceType
        The Music Service chosen by the Server Operator. Game Sessions use it
        unless the Host picks another available one.
    port : int
        The port the server listens on; `run` replaces it with the port it binds.
    music_services : Mapping[MusicServiceType, MusicServiceDescription]
        The description of each Music Service: whether it can work here and how
        to build its adapter for a new Game Session.
    """

    def __init__(
        self,
        music_service: MusicServiceType,
        port: int = config.DEFAULT_PORT,
        music_services: Mapping[
            MusicServiceType, MusicServiceDescription
        ] = MUSIC_SERVICES,
    ) -> None:
        self.music_service = music_service
        self.music_services = music_services
        self.available_music_services = available_music_services(
            music_service, music_services
        )
        self.port = port
        self.app = self.create_app()
        self._ready_callbacks: list[Callable[[], None]] = []

    def call_when_ready(self, callback: Callable[[], None]) -> None:
        """Run the callback once the server accepts connections."""
        self._ready_callbacks.append(callback)

    def _serve(
        self, port: int, ssl_keyfile: str | None = None, ssl_certfile: str | None = None
    ) -> None:
        uvicorn_config = uvicorn.Config(
            self.app,
            host="0.0.0.0",  # noqa: S104
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
        )
        _ReadyNotifyingServer(uvicorn_config, self._ready_callbacks).run()

    def run(self, port: int) -> None:
        """Start the Uvicorn server."""
        self.port = port
        ssl_files = _ssl_files()
        lan_addresses = network.lan_ipv4_addresses_or_empty()
        print(
            startup_hint(
                port, use_ssl=ssl_files is not None, lan_addresses=lan_addresses
            )
        )

        if ssl_files is not None:
            logger.info("Running server with SSL.")
            ssl_keyfile, ssl_certfile = ssl_files
            self._serve(port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
        else:
            logger.info("Running server without SSL.")
            self._serve(port)

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
        app.get("/music-services")(self._list_music_services)
        app.get(
            COVER_URL_PREFIX + "{cover_id}",
            response_class=Response,
            responses={
                200: {"content": {"image/jpeg": {}}},
                404: {"description": "Unknown cover."},
            },
        )(self._get_cover)
        app.get(
            "/join-qr.svg",
            response_class=Response,
            responses={
                200: {"content": {"image/svg+xml": {}}},
                404: {"description": "Unknown Game Session."},
            },
        )(self._get_join_qr)
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

        build = self.music_services[music_service_type].build
        if build is None:
            raise HTTPException(
                status_code=400,
                detail=self.music_services[music_service_type].login_hint,
            )
        try:
            music_service = build()
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

    async def _list_music_services(self) -> MusicServicesResponse:
        return MusicServicesResponse(
            default=self.music_service, available=self.available_music_services
        )

    async def _list_joinable_game_sessions(self) -> JSONResponse:
        joinable_session_names = game_session_manager.joinable_session_names()
        return JSONResponse(content={"sessions": joinable_session_names})

    @staticmethod
    async def _get_cover(cover_id: str) -> Response:
        image = cover_store.get(cover_id)
        if image is None:
            raise HTTPException(status_code=404, detail="Unknown cover.")
        return Response(content=image, media_type="image/jpeg")

    async def _get_join_qr(self, session: SessionName) -> Response:
        if not game_session_manager.get_game_session(session):
            raise HTTPException(
                status_code=404, detail=f"Game session {session} not found."
            )
        lan_addresses = network.lan_ipv4_addresses_or_empty()
        host = lan_addresses[0] if lan_addresses else "localhost"
        url = base_url(host, self.port, use_ssl=uses_ssl()) + join_qr.join_path(session)
        return Response(content=join_qr.render_svg(url), media_type="image/svg+xml")

    async def _join_game_session(self, req: JoinGameRequest) -> JSONResponse:
        game_session_manager.remove_expired_sessions()
        session_name = req.game_id
        user_name = req.user_name
        session = game_session_manager.get_game_session(session_name)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {session_name} not found."
            )
        rejoin = session.is_running
        await session.connection_manager.deliver(session.join(user_name))
        if rejoin:
            message = f"Player {user_name} can rejoin game session {session_name}."
        else:
            message = f"Player {user_name} joined game session {session_name}."
        return JSONResponse(content={"message": message})

    async def _start_game_session(self, req: StartGameRequest) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        session_name = req.game_id
        session = game_session_manager.get_game_session(session_name)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Game session {session_name} not found."
            )

        await session.connection_manager.deliver(session.start())

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

        try:
            outgoing = game_session.connect(username)
        except GameSessionOverError as e:
            await _send(websocket, game_over_message(e.winner))
            await websocket.close()
            return
        except (NotAPlayerError, AlreadyConnectedError) as e:
            await _send(websocket, error_message(str(e)))
            await websocket.close(code=1008)
            return

        connection_manager = game_session.connection_manager
        connection_manager.attach(username, websocket)
        await connection_manager.deliver(outgoing)

        try:
            while True:
                raw_data = await websocket.receive_text()
                await self._handle_message(
                    ClientMessageContext(websocket, username, game_session), raw_data
                )
        except WebSocketDisconnect:
            connection_manager.detach(username)
            await connection_manager.deliver(game_session.disconnect(username))
            game_session_manager.release_if_empty(game_session)

    @staticmethod
    async def _handle_message(context: ClientMessageContext, raw_data: str) -> None:
        """Parse one client message and dispatch it."""
        websocket = context.websocket
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            await _send(websocket, error_message("Invalid JSON."))
            return
        if not isinstance(data, dict):
            await _send(websocket, error_message("Expected an object."))
            return

        message_type = data.get("type")
        client_handler = (
            CLIENT_MESSAGE_HANDLERS.get(message_type)
            if isinstance(message_type, str)
            else None
        )
        if client_handler is None:
            await _send(websocket, error_message("Unknown message type."))
            return
        await client_handler(context, data)
