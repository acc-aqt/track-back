import asyncio
import threading
import pytest
from cli.client import CliClient
from backend.server.server import Server, GameContext
from backend.music_service.mock import DummyMusicService
import time
from multiprocessing import Process, Queue


def run_server_with_queue(port, result_queue):
    game_context = GameContext(
        target_song_count=2,
        music_service=DummyMusicService(),
    )
    server = Server(game_context=game_context, port=port)
    server.run()

    result_queue.put(
        {
            "winner": game_context.game.winner.name,
            "song_count": len(game_context.game.winner.song_list),
        }
    )


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

    result_queue = Queue()

    server_process = Process(target=run_server_with_queue, args=(port, result_queue))
    server_process.start()
    await asyncio.sleep(2)  # Wait for server to start

    # Start CLI client and play
    client = CliClient(username, host, port, stop_after_turns=2)
    await client.run()

    # Assertions: check winner and song list length
    result = result_queue.get(timeout=5)
    assert result["winner"] == "Alice"
    assert result["song_count"] == 2

    # ✅ Kill server after test
    server_process.terminate()
    server_process.join()
