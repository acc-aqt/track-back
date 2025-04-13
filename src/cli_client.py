import argparse
import asyncio
import json
import websockets


class CliClient:
    def __init__(self, username, port):
        self.username = username
        self.port = port
        self.uri = f"ws://localhost:{self.port}/ws/{self.username}"

    async def play(self):
        try:
            async with websockets.connect(self.uri) as websocket:
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
                        await self._handle_welcome(data)
                    elif msg_type == "guess_result":
                        await self._handle_guess_result(data)
                    elif msg_type == "your_turn" and data.get("next_player") == self.username:
                        await self._handle_your_turn(data, websocket)
                    elif msg_type == "turn_result":
                        await self._handle_turn_result(data)
                    elif msg_type == "game_over":
                        await self._handle_game_over(data)
                        break
                    else:
                        print(f"\n📬 Unhandled message:\n{json.dumps(data, indent=2)}")

        except OSError as e:
            print(f"🚨 Failed to connect to server at {self.uri}: {e}")
            retry = input("🔁 Retry? (y/n): ")
            if retry.lower() == "y":
                await self.play()
                
    async def _handle_welcome(self, data: dict):
        print(f"👋 {data['message']}")

    async def _handle_guess_result(self, data: dict):
        if data.get("player") == self.username:
            print(f"🎯 Result: {data['result']} — {data['message']}")

    async def _handle_your_turn(self, data: dict, websocket):
        print(f"\n🎮 It's your turn, {self.username}!")

        song_list = data.get("song_list", [])
        self._print_song_list(song_list)

        try:
            index_range = f"[0–{len(song_list)}]"
            index = int(input(f"📍 Where do you want to insert this song? Index {index_range}: "))
        except ValueError:
            print("⚠️ Please enter a valid number.")
            return

        guess = {"type": "guess", "index": index}
        await websocket.send(json.dumps(guess))

    def _print_song_list(self, song_list):
        if song_list:
            print("\n📻 Your current song list:")
            for i, song in enumerate(song_list):
                print(f"  [{i}] {song['release_year']} | '{song['title']}' by {song['artist']}")

    async def _handle_turn_result(self, data: dict):
        print(f"🪄 {data['player']} made a move: {data['message']}")

    async def _handle_game_over(self, data: dict):
        print(f"🏁 Game Over! Winner: {data['winner']}")


def main():
    parser = argparse.ArgumentParser(description="CLI client for TrackBack Game")
    parser.add_argument("--name", type=str, help="Your username")
    parser.add_argument("--port", type=int, default=4200, help="Server port (default: 4200)")

    args = parser.parse_args()
    username = args.name or input("👤 Enter your username: ")

    client = CliClient(username, args.port)
    asyncio.run(client.play())


if __name__ == "__main__":
    main()
