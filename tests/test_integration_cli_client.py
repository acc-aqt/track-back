import asyncio
import threading
import pytest
from cli.client import CliClient
from backend.server.server import Server, GameContext
from backend.music_service.mock import DummyMusicService
import time


@pytest.mark.asyncio
async def test_single_player_game_flow(monkeypatch):
    host = "localhost"
    port = 4242
    username = "Alice"

    input_sequence = iter(["y", "0", "1"])

    def delayed_input(prompt):
        time.sleep(2)  # Give the client/server time to process the last action
        return next(input_sequence)

    monkeypatch.setattr("builtins.input", delayed_input)

    game_context = GameContext(
        target_song_count=2,
        music_service=DummyMusicService(),
    )
    server = Server(game_context=game_context, port=port)

    def run_server():
        server.run()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    await asyncio.sleep(2)  # Give server time to spin up

    # Start CLI client and play
    client = CliClient(username, host, port, stop_after_turns=2)
    await client.run()

    # Assertions: check winner and song list length
    user = game_context.registered_users[username]
    assert len(user.song_list) == 2
    assert game_context.game.winner == user
