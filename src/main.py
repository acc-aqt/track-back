"""Entry point to start the track-back server."""

import os
import signal
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

        await ws.send_text(json.dumps({
            "type": "your_turn",
            "message": "🎮 It's your turn!",
            "next_player": first_player.name,
            "next_song": first_song.title,
            "song_list": ctx.game._serialize_song_list(first_player.song_list)
        }))

        return {"message": "Game started!", "first_player": first_player.name}

    @app.websocket("/ws/{username}")
    async def websocket_endpoint(websocket: WebSocket, username: str):
        await websocket.accept()
        ctx: GameContext = websocket.app.state.ctx

        await handle_connection(ctx, websocket, username)

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                if data.get("type") == "guess":
                    index = data.get("index")
                    await handle_guess(ctx, websocket, username, index)

                else:
                    await websocket.send_text("❓ Unknown message type.")

        except WebSocketDisconnect:
            print(f"User {username} disconnected")
            ctx.connected_users.pop(username, None)

    return app

async def handle_connection(ctx: GameContext, websocket: WebSocket, username: str):
    if username in ctx.registered_users:
        await websocket.send_text(f"✅ Welcome back, {username}!")
    else:
        ctx.registered_users[username] = User(name=username)
        await websocket.send_text(f"✅ Welcome, {username}! You've been registered.")
    
    ctx.connected_users[username] = websocket

async def handle_guess(ctx: GameContext, websocket: WebSocket, username: str, index: int):
    if ctx.game is None:
        await websocket.send_text("⚠️ Game has not started yet.")
        return

    result = ctx.game.process_turn(username, index)

    # Send guess result to the player
    await websocket.send_text(json.dumps({
        "type": "guess_result",
        "player": username,
        "result": result["result"],
        "message": result["message"],
        "song_list": result["song_list"]
    }))

    # Game over?
    if result.get("game_over"):
        await broadcast_game_over(ctx, result["winner"])
        os.kill(os.getpid(), signal.SIGINT)
        return

    # Notify other players
    await broadcast_turn_result(ctx, username, result)

    # Notify next player
    await notify_next_player(ctx, result["next_player"], result["next_song"])

async def broadcast_turn_result(ctx: GameContext, current_player: str, result: dict):
    for name, ws in ctx.connected_users.items():
        if name != current_player:
            await ws.send_text(json.dumps({
                "type": "turn_result",
                "player": current_player,
                "result": result["result"],
                "message": result["message"],
                "next_player": result["next_player"]
            }))
            
async def notify_next_player(ctx: GameContext, next_player: str, next_song: str):
    if next_player in ctx.connected_users:
        ws = ctx.connected_users[next_player]
        await ws.send_text(json.dumps({
            "type": "your_turn",
            "next_player": next_player,
            "next_song": next_song,
            "song_list": ctx.game._serialize_song_list(ctx.registered_users[next_player].song_list)
        }))
        
async def broadcast_game_over(ctx: GameContext, winner: str):
    for _, ws in ctx.connected_users.items():
        await ws.send_text(json.dumps({
            "type": "game_over",
            "winner": winner,
            "message": f"🏆 {winner} has won the game!"
        }))
    print("💥 Game over, shutting down server...")
            
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_song_count", type=int, default=5)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    load_dotenv()
    config = load_user_config()
    music_service = MusicServiceFactory.create_music_service(config["music_service"])

    app = create_app(target_song_count=args.target_song_count, music_service=music_service)
    uvicorn.run(app, port=args.port)


if __name__ == "__main__":
    main()