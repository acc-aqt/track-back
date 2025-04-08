import asyncio
import websockets
import json

PORT = "4200"


async def play(username: str):
    uri = f"ws://localhost:{PORT}/ws/{username}"
    async with websockets.connect(uri) as websocket:
        welcome = await websocket.recv()
        print(f"🛰️ Server: {welcome}")
        client_count = 0
        while True:
            client_count += 1

            try:
                server_msg = await websocket.recv()
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Connection to server closed. Goodbye!")
                break
            try:
                data = json.loads(server_msg)
            except json.JSONDecodeError:
                print(f"Server (raw): {server_msg}")
                continue
            # print(f"\n📬 New message:\n{json.dumps(data, indent=2)}")
            # print(f" Client count: {client_count}")
            msg_type = data.get("type")

            # ⬇️ Handle the result of your previous move
            if msg_type == "guess_result" and data.get("player") == username:
                print(f"🎯 Result: {data['result']} — {data['message']}")

            # ⬇️ Handle when it's your turn to play
            elif msg_type == "your_turn" and data.get("next_player") == username:
                print(f"\n🎮 It's your turn, {username}!")

                if "song_list" in data:
                    print("\n📻 Your current song list:")
                    for i, song in enumerate(data["song_list"]):
                        print(f"  [{i}] {song['release_year']} | '{song['title']}' by {song['artist']}")

                # song_title = data.get("next_song", "Unknown")
                # print(f"\n🎶 Current song: {song_title}")

                try:
                    index = int(input("📍 Where do you want to insert this song? Index: "))
                except ValueError:
                    print("⚠️ Please enter a valid number.")
                    return

                guess = {"type": "guess", "index": index}
                await websocket.send(json.dumps(guess))

            # ⬇️ Handle someone else's turn result
            elif msg_type == "turn_result":
                print(f"🪄 {data['player']} made a move: {data['message']}")

            # ⬇️ Handle game over
            elif msg_type == "game_over":
                print(f"🏁 Game Over! Winner: {data['winner']}")
                break

            # ⬇️ Catch-all for unknown messages
            else:
                print(f"\n📬 Unhandled message:\n{json.dumps(data, indent=2)}")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str)
    args = parser.parse_args()
    username = args.name

    if not username:
        username = input("👤 Enter your username: ")

    asyncio.run(play(username))


if __name__ == "__main__":
    main()
