"""Entry point to start the track-back server."""

import argparse
import json
import os
import signal
import tomllib
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.track_back_game import TrackBackGame
from game.user import User, UserRegister
from local_ip import get_local_ip
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


class Server:
    def __init__(self, game_context, port):
        self.game_context = game_context
        self.app = self.create_app()
        self.port = port
        ip = get_local_ip()
        self.url = f"http://{ip}:{port}/"
        print(f"\n🌍 Game server running at: {self.url}\n")

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)

    def create_app(self) -> FastAPI:
        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.state.ctx = self.game_context

        @app.post("/shutdown")
        async def shutdown(request: Request):
            print("🛑 Shutdown requested via web UI")
            os.kill(os.getpid(), signal.SIGINT)
            return {"message": "Server is shutting down..."}

        @app.post("/register")
        async def register(user: UserRegister):
            if user.name in self.game_context.registered_users:
                return {"error": f"User '{user.name}' already registered"}
            self.game_context.registered_users[user.name] = User(
                name=user.name
            )
            return {"message": f"User '{user.name}' registered successfully."}

        @app.post("/start")
        async def start_game():
            if len(self.game_context.registered_users) < 1:
                return {"error": "Not enough players to start the game."}

            users = list(self.game_context.registered_users.values())
            self.game_context.game = TrackBackGame(
                users,
                self.game_context.target_song_count,
                self.game_context.music_service,
            )
            self.game_context.game.start_game()

            first_player = self.game_context.game.get_current_player()
            first_song = self.game_context.game.get_current_song()

            ws = self.game_context.connected_users.get(first_player.name)
            if not ws:
                return {
                    "error": f"{first_player.name} is not connected via WebSocket."
                }

            await ws.send_text(
                json.dumps(
                    {
                        "type": "your_turn",
                        "message": "🎮 It's your turn!",
                        "next_player": first_player.name,
                        "next_song": first_song.title,
                        "song_list": self.game_context.game._serialize_song_list(
                            first_player.song_list
                        ),
                    }
                )
            )

            return {
                "message": "Game started!",
                "first_player": first_player.name,
            }

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
    music_service = MusicServiceFactory.create_music_service(
        config["music_service"]
    )
    game_context = GameContext(
        target_song_count=args.target_song_count, music_service=music_service
    )
    server = Server(game_context=game_context, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
