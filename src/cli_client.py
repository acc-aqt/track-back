import argparse
import asyncio
import json
import websockets


async def handle_welcome(data: dict):
    print(f"👋 {data['message']}")


async def handle_guess_result(data: dict, username: str):
    if data.get("player") == username:
        print(f"🎯 Result: {data['result']} — {data['message']}")


async def handle_your_turn(data: dict, websocket, username: str):
    print(f"\n🎮 It's your turn, {username}!")

    song_list = data.get("song_list", [])
    if song_list:
        print("\n📻 Your current song list:")
        for i, song in enumerate(song_list):
            print(f"  [{i}] {song['release_year']} | '{song['title']}' by {song['artist']}")

    try:
        index_range = f"[0–{len(song_list)}]"
        index = int(input(f"📍 Where do you want to insert this song? Index {index_range}: "))
    except ValueError:
        print("⚠️ Please enter a valid number.")
        return

    guess = {"type": "guess", "index": index}
    await websocket.send(json.dumps(guess))


async def handle_turn_result(data: dict):
    print(f"🪄 {data['player']} made a move: {data['message']}")


async def handle_game_over(data: dict):
    print(f"🏁 Game Over! Winner: {data['winner']}")


async def play(username: str, port: int):
    uri = f"ws://localhost:{port}/ws/{username}"
    try:
        async with websockets.connect(uri) as websocket:
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 Connection to server closed. Goodbye!")
                    break
                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON from server:\n{message}")
                    continue

                msg_type = data.get("type")
                if not msg_type:
                    print(f"⚠️ Malformed message:\n{data}")
                    continue

                # Dispatch based on message type
                if msg_type == "welcome":
                    await handle_welcome(data)
                elif msg_type == "guess_result":
                    await handle_guess_result(data, username)
                elif msg_type == "your_turn" and data.get("next_player") == username:
                    await handle_your_turn(data, websocket, username)
                elif msg_type == "turn_result":
                    await handle_turn_result(data)
                elif msg_type == "game_over":
                    await handle_game_over(data)
                    break
                else:
                    print(f"\n📬 Unhandled message:\n{json.dumps(data, indent=2)}")

    except OSError as e:
        print(f"🚨 Failed to connect to server at {uri}: {e}")


def main():
    parser = argparse.ArgumentParser(description="CLI client for TrackBack Game")
    parser.add_argument("--name", type=str, help="Your username")
    parser.add_argument("--port", type=int, default=4200, help="Server port (default: 4200)")

    args = parser.parse_args()
    username = args.name or input("👤 Enter your username: ")
    asyncio.run(play(username, args.port))


if __name__ == "__main__":
    main()
    