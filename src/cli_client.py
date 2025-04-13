import argparse
import asyncio
import json
import websockets


class CliClient:
    def __init__(self, username, host, port):
        self.username = username
        self.uri = f"ws://{host}:{port}/ws/{username}"

    async def play(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                await self._handle_messages(websocket)

        except OSError as e:
            print(f"🚨 Failed to connect to server at {self.uri}: {e}")
            retry = input("🔁 Retry? (y/n): ")
            if retry.lower() == "y":
                await self.play()

    async def _handle_messages(self, websocket):
        while True:
            data = await self._receive_json(websocket)
            if not data:
                break

            msg_type = data.get("type")
            if not msg_type:
                print(f"⚠️ Malformed message:\n{data}")
                continue

            await self._dispatch_message(msg_type, data, websocket)

    async def _dispatch_message(self, msg_type: str, data: dict, websocket):
        """Dispatch incoming messages to the appropriate handler."""
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
        else:
            print(f"\n📬 Unhandled message:\n{json.dumps(data, indent=2)}")

    async def _receive_json(self, websocket) -> dict | None:
        """Receive and parse a JSON message from the server."""
        try:
            message = await websocket.recv()
            return json.loads(message)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection to server closed. Goodbye!")
            return None
        except json.JSONDecodeError:
            print("⚠️ Received invalid JSON.")
            return {}

    async def _handle_welcome(self, data: dict):
        print(f"👋 {data['message']}")

    async def _handle_guess_result(self, data: dict):
        if data.get("player") == self.username:
            print(f"🎯 Result: {data['result']} — {data['message']}")

    async def _handle_your_turn(self, data: dict, websocket):
        print(f"\n🎮 It's your turn, {self.username}!")

        song_list = data.get("song_list", [])
        self._print_song_list(song_list)

        index = self._get_valid_index(song_list)

        guess = {"type": "guess", "index": index}
        await websocket.send(json.dumps(guess))

    def _get_valid_index(self, song_list):
        while True:
            try:
                index_range = f"[0–{len(song_list)}]"
                index = int(
                    input(f"📍 Where do you want to insert this song? Index {index_range}: ")
                )
            except ValueError:
                print("⚠️ Please enter a valid number.")
                continue
            if 0 <= index <= len(song_list):
                return index

            print(f"⚠️ Invalid index. Please enter a number between 0 and {len(song_list)}.")

    def _print_song_list(self, song_list):
        if not song_list:
            return

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
    parser.add_argument(
        "--host", type=str, default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument("--port", type=int, default=4200, help="Server port (default: 4200)")

    args = parser.parse_args()
    username = args.name or input("👤 Enter your username: ")

    client = CliClient(username, args.host, args.port)
    asyncio.run(client.play())


if __name__ == "__main__":
    main()
