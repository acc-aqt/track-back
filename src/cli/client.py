"""Command line client for the TrackBack game."""

import json
from typing import Any, cast

import httpx
import websockets
from websockets.asyncio.client import ClientConnection

from backend.game.song import Song, deserialize_song

HTTP_OK = 200


class CliClient:
    """CLI client for the TrackBack game."""

    def __init__(
        self, username: str, host: str, port: int, stop_after_turns: int | None = None
    ) -> None:
        self.username = username
        self.uri = f"ws://{host}:{port}/ws/{username}"
        self.url = f"http://{host}:{port}"
        self.turn_counter = 0
        self.stop_after_turns = stop_after_turns
        self.websocket: ClientConnection | None = None

    async def start_game(self) -> None:
        """Send a POST request to the server to start the game."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.url}/start")
                data = response.json()
                if response.status_code == HTTP_OK:
                    print("🚀 Game started.")
                else:
                    print(f"❌ Failed to start game. Retrieved following data: {data}")
        except httpx.RequestError as e:
            print(f"❌ Error starting game: {e}")

    async def run(self) -> None:
        """Run the CLI client."""
        try:
            async with websockets.connect(self.uri) as websocket:
                self.websocket = websocket
                await self._handle_messages()

        except OSError as e:
            print(f"🚨 Failed to connect to server at {self.uri}: {e}")
            retry = input("🔁 Retry? (y/n): ")
            if retry.lower() == "y":
                await self.run()

    async def _handle_messages(self) -> None:
        while True:
            data = await self._receive_json()
            if not data:
                break

            msg_type = data.get("type")
            if not msg_type:
                print(f"⚠️ Malformed message:\n{data}")
                continue

            await self._dispatch_message(msg_type, data)

    async def _dispatch_message(self, msg_type: str, data: dict[str, str]) -> None:
        """Dispatch incoming messages to the appropriate handler."""
        if msg_type == "welcome":
            await self._handle_welcome(data)
        elif msg_type == "guess_result":
            await self._handle_guess_result(data)
        elif msg_type == "your_turn" and data.get("next_player") == self.username:
            await self._handle_your_turn(data)
        elif msg_type == "turn_result":
            await self._handle_turn_result(data)
        elif msg_type == "game_over":
            await self._handle_game_over(data)
        else:
            print(f"\n📬 Unhandled message:\n{json.dumps(data, indent=2)}")

    async def _receive_json(self) -> dict[str, Any]:
        """Receive and parse a JSON message from the server."""
        if self.websocket is None:
            print("⚠️ WebSocket connection not established.")
            return {}

        try:
            message = await self.websocket.recv()
            return cast(dict[str, Any], json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection to server closed. Goodbye!")
            return {}
        except json.JSONDecodeError:
            print("⚠️ Received invalid JSON.")
            return {}

    async def _handle_welcome(self, data: dict[str, str]) -> None:
        print(f"👋 {data['message']}")
        await self._start_game_by_user_input(data)

    async def _start_game_by_user_input(self, data: dict[str, str]) -> None:
        if data.get("first_player"):
            choice = input("🎮 Start game now? (y/n): ").lower()
            if choice == "y":
                await self.start_game()
            else:
                await self._start_game_by_user_input(data)
        else:
            print("🕐 Waiting for game to start...")

    async def _handle_guess_result(self, data: dict[str, str]) -> None:
        if data.get("player") == self.username:
            print(f"🎯 Result: {data['result']} — {data['message']}")

    async def _handle_your_turn(self, data: dict[str, str]) -> None:
        print(f"\n🎮 It's your turn, {self.username}!")

        song_list = [deserialize_song(song) for song in data.get("song_list", [])]
        self._print_song_list(song_list)

        index = self._get_valid_index(max_index=len(song_list))

        guess = {"type": "guess", "index": index}
        if not self.websocket:
            print("⚠️ WebSocket connection not established.")
            return

        await self.websocket.send(json.dumps(guess))
        # ✅ After sending a guess, increase turn counter
        if self.stop_after_turns is not None:
            self.turn_counter += 1
            if self.turn_counter >= self.stop_after_turns:
                print("✅ Max turns reached, exiting.")
                await self.websocket.close()

    def _get_valid_index(self, max_index: int) -> int:
        while True:
            try:
                index_range = f"[0-{max_index}]"
                index = int(
                    input(
                        "📍 Where do you want to insert this song?"
                        f"Index {index_range}: "
                    )
                )
            except ValueError:
                print("⚠️ Please enter a valid number.")
                continue
            if 0 <= index <= max_index:
                return index

            print(f"⚠️ Invalid index. Please enter a number between 0 and {max_index}.")

    def _print_song_list(self, song_list: list[Song]) -> None:
        if not song_list:
            return

        print("\n📻 Your current song list:")
        for i, song in enumerate(song_list):
            print(f"  [{i}] {song.release_year} | '{song.title}' by {song.artist}")

    async def _handle_turn_result(self, data: dict[str, str]) -> None:
        print(f"🪄 {data['player']} made a move: {data['message']}")

    async def _handle_game_over(self, data: dict[str, str]) -> None:
        print(f"🏁 Game Over! Winner: {data['winner']}")


async def play_on_cli(username: str, host: str, port: int) -> None:
    """Run the CLI client."""
    client = CliClient(username, host, port)
    await client.run()
