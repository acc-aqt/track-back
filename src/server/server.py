"""Contains the game server class for managing game state and WebSocket connections."""

import json
import logging


import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from game.user import User
from music_service.spotify import router as spotify_auth_router
from server.websocket_handler import WebSocketGameHandler
from server.game_sessions import game_session_manager
from game.game_logic import GameLogic
from music_service.factory import MusicServiceFactory

from pydantic import BaseModel


class CreateGameRequest(BaseModel):
    game_id: str
    target_song_count: int
    music_service_type: str


class JoinGameRequest(BaseModel):
    game_id: str
    user_name: str


class StartGameRequest(BaseModel):
    game_id: str


class Server:
    """Encapsulates the FastAPI application."""

    def __init__(self) -> None:
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

        app.post("/create")(self._create_game_session)
        app.get("/list-sessions")(self._list_joinable_game_sessions)
        app.post("/join")(self._join_game_session)
        app.post("/start")(self._start_game_session)
        app.websocket("/ws/{game_id}/{username}")(self._websocket_endpoint)
        app.include_router(spotify_auth_router)

        return app

    async def _create_game_session(self, req: CreateGameRequest):
        game_id = req.game_id
        target_song_count = req.target_song_count

        game = GameLogic(target_song_count=target_song_count)
        game_session_manager.add_game(game_id, game)

        music_service_type = req.music_service_type
        music_service = MusicServiceFactory.create_music_service(music_service_type)
        game.set_music_service(music_service)

        return JSONResponse(content={"message": f"Game session {game_id} created."})

    async def _list_joinable_game_sessions(self) -> JSONResponse:
        joinable_session_ids = [
            session_id
            for session_id, session in game_session_manager.sessions.items()
            if not session.game_logic.running
        ]
        return JSONResponse(content={"sessions": joinable_session_ids})

    async def _join_game_session(self, req: JoinGameRequest) -> JSONResponse:
        game_id = req.game_id
        user_name = req.user_name
        session = game_session_manager.get_game_session(game_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Game session {game_id} not found.")
        
        session.connection_manager.register_user(user_name)
        return JSONResponse(content={"message": f"User {user_name} joined game {game_id}."})

    async def _start_game_session(self, req: StartGameRequest) -> JSONResponse:
        """Start the game and notify the first player via WebSocket."""
        game_id = req.game_id
        session = game_session_manager.get_game_session(game_id)

        connection_manager = session.connection_manager

        if len(connection_manager.get_registered_user_names()) < 1:
            raise HTTPException(status_code=400, detail="Not enough players to start the game.")

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

    async def _websocket_endpoint(self, websocket: WebSocket, game_id: str, username: str):
        await websocket.accept()
        game_session = game_session_manager.get_game_session(game_id)
        connection_manager = game_session.connection_manager
        if connection_manager.first_player is None:
            connection_manager.first_player = username
            logging.info("First player: %s", connection_manager.first_player)

        handler = WebSocketGameHandler(connection_manager)
        await handler.handle_connection(websocket, username)

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
            logging.info("User %s disconnected", username)
            session = game_session_manager.get_game_session(game_id)
            connection_manager = session.connection_manager
            game = session.game_logic

            connection_manager.unregister_user(username)
            user_list_before = len(game.users)
            game.users = [u for u in game.users if u.name != username]
            user_list_after = len(game.users)

            if user_list_after < user_list_before:
                logging.info(f"Removed {username} from game '{game_id}'.")
                if not game.users:
                    game_session_manager.remove_game_session(game_id)
                    logging.info(f"Removed empty game session '{game_id}'.")
