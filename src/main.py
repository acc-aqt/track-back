"""Entry point to start the track-back server."""

import json
import tomllib
import argparse
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.track_back_game import TrackBackGame
from game.user import User, UserRegister
from music_service.factory import MusicServiceFactory
from websocket_handler import WebSocketGameHandler


class GameContext:
    def __init__(self, target_song_count: int, music_service):
        self.target_song_count = target_song_count
        self.music_service = music_service
        self.game: TrackBackGame | None = None
        self.connected_users: dict[str, WebSocket] = {}
        self.registered_users: dict[str, User] = {}


def load_user_config(config_path: str = "config.toml") -> dict[str, str]:
    with Path(config_path).open("rb") as f:
        return tomllib.load(f)


def create_app(target_song_count: int, music_service) -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ctx = GameContext(target_song_count, music_service)
    app.state.ctx = ctx

    @app.post("/register")
    async def register(user: UserRegister):
        if user.name in ctx.registered_users:
            return {"error": f"User '{user.name}' already registered"}
        ctx.registered_users[user.name] = User(name=user.name)
        return {"message": f"User '{user.name}' registered successfully."}

    @app.post("/start")
    async def start_game():
        if len(ctx.registered_users) < 1:
            return {"error": "Not enough players to start the game."}

        users = list(ctx.registered_users.values())
        ctx.game = TrackBackGame(users, ctx.target_song_count, ctx.music_service)
        ctx.game.start_game()

        first_player = ctx.game.get_current_player()
        first_song = ctx.game.get_current_song()

        ws = ctx.connected_users.get(first_player.name)
        if not ws:
            return {"error": f"{first_player.name} is not connected via WebSocket."}

        await ws.send_text(
            json.dumps(
                {
                    "type": "your_turn",
                    "message": "🎮 It's your turn!",
                    "next_player": first_player.name,
                    "next_song": first_song.title,
                    "song_list": ctx.game._serialize_song_list(first_player.song_list),
                }
            )
        )

        return {"message": "Game started!", "first_player": first_player.name}

    @app.websocket("/ws/{username}")
    async def websocket_endpoint(websocket: WebSocket, username: str):
        await websocket.accept()
        ctx = websocket.app.state.ctx
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
            print(f"User {username} disconnected")
            ctx.connected_users.pop(username, None)            

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_song_count", type=int, default=3)
    parser.add_argument("--port", type=int, default=4200)
    args = parser.parse_args()

    load_dotenv()
    config = load_user_config()
    music_service = MusicServiceFactory.create_music_service(config["music_service"])

    app = create_app(target_song_count=args.target_song_count, music_service=music_service)
    uvicorn.run(app, port=args.port)


if __name__ == "__main__":
    main()
