"""Entry point to start the track-back server."""

import os
import signal
import uvicorn
import argparse
import json
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.track_back_game import TrackBackGame
from game.user import User, UserRegister, get_users
from music_service.factory import MusicServiceFactory


def load_user_config(config_path: str = "config.toml") -> dict[str, str]:
    """Load user configuration from a TOML file."""
    with Path(config_path).open("rb") as f:
        return tomllib.load(f)


load_dotenv()  # load credentials from .env file

config = load_user_config()

provider = config.get("music_service")
music_service = MusicServiceFactory.create_music_service(provider)

# Placeholder for the game
game: TrackBackGame | None = None


def create_app(target_song_count: int) -> FastAPI:
    app = FastAPI()

    # Allow frontend/dev clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    connected_users: dict[str, WebSocket] = {}
    registered_users: dict[str, User] = {}

    # curl -X POST http://localhost:8000/start
    @app.post("/start")
    async def start_game():
        global game

        if len(registered_users) < 1:
            return {"error": "Not enough players to start the game."}

        users = list(registered_users.values())

        game = TrackBackGame(
            users, target_song_count=target_song_count, music_service=music_service
        )
        game.start_game()

        # Send first song + turn info to the first player
        first_player = game.get_current_player()
        first_song = game.get_current_song()

        ws = connected_users.get(first_player.name)
        if not ws:
            return {"error": f"{first_player.name} is not connected via WebSocket."}
        await ws.send_text(
            json.dumps({
                "type": "your_turn", 
                "message": "🎮 It's your turn!",
                "next_player": first_player.name,
                "next_song": first_song.title,
                "song_list": [
                    {"title": s.title, "artist": s.artist, "release_year": s.release_year}
                    for s in first_player.song_list
                ]
            })
        )

        return {"message": "Game started!", "first_player": first_player.name}

    @app.websocket("/ws/{username}")
    async def websocket_endpoint(websocket: WebSocket, username: str):
        await websocket.accept()

        if username in registered_users:
            await websocket.send_text("❌ User with name {username} already exists.")
            await websocket.close()
            return

        user = User(name=username)

        registered_users[username] = user

        connected_users[username] = websocket
        await websocket.send_text(f"✅ Welcome, {username}! You're connected.")

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                if data.get("type") == "guess":
                    index = data.get("index")

                    if game is None:
                        await websocket.send_text("⚠️ Game has not started yet.")
                        continue

                    result = game.process_turn(username, index)

                    # 🎯 Send the result of the guess back to the player
                    await websocket.send_text(json.dumps({
                        "type": "guess_result",
                        "player": username,
                        "result": result["result"],
                        "message": result["message"],
                        "song_list": result["song_list"]
                    }))

                    # 🏁 If the game is over, notify everyone
                    if result.get("game_over"):
                        for _, ws in connected_users.items():
                            await ws.send_text(json.dumps({
                                "type": "game_over",
                                "winner": result["winner"],
                                "message": f"🏆 {result['winner']} has won the game!"
                            }))
                        print("💥 Game over, shutting down server...")
                        os.kill(os.getpid(), signal.SIGINT)
                        return

                    # 🔄 Notify other players of the move
                    for other_name, other_ws in connected_users.items():
                        if other_name != username:
                            await other_ws.send_text(json.dumps({
                                "type": "turn_result",
                                "player": username,
                                "result": result["result"],
                                "message": result["message"],
                                "next_player": result["next_player"]
                            }))

                    # 🎮 Tell the next player it's their turn
                    next_player = result["next_player"]
                    if next_player in connected_users:
                        next_ws = connected_users[next_player]
                        await next_ws.send_text(json.dumps({
                            "type": "your_turn",
                            "next_player": next_player,
                            "next_song": result["next_song"],
                            "song_list": game._serialize_song_list(registered_users[next_player].song_list)
                        }))

                else:
                    await websocket.send_text("❓ Unknown message type.")

        except WebSocketDisconnect:
            print(f"User {username} disconnected")
            connected_users.pop(username, None)

    return app


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--target_song_count", type=int, default=5)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app(target_song_count=args.target_song_count)

    uvicorn.run(
        app,
        # host="0.0.0.0",
        port=args.port,
    )


if __name__ == "__main__":
    main()
