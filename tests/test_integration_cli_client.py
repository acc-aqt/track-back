import asyncio
import json
import socket

import pytest
import subprocess
import time
import requests
import websockets

PORT = 9000
BASE_URL = f"http://localhost:{PORT}"
WS_URL = "ws://localhost:{PORT}/ws"

def wait_for_port(host, port, timeout=10.0):
    """Wait for a port to start accepting connections."""
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.1)
        if time.time() - start > timeout:
            raise TimeoutError(f"Timed out waiting for {host}:{port} to be ready")
        
@pytest.fixture(scope="module")
def fastapi_server():
    """Launch the FastAPI server before the test and kill it after."""
    server = subprocess.Popen(
        [
            "python",
            "main.py",  # <-- Run your entry point directly
            "--target_song_count",
            "1",  # <-- Custom argument
            "--port",
            str(PORT),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    try:
        wait_for_port("localhost", PORT, timeout=10)
    except TimeoutError:
        server.kill()
        raise RuntimeError("❌ FastAPI server failed to start in time")

    yield

    server.kill()
    server.wait()


async def simulate_player(username, guess_index, game_done_event):
    uri = f"{WS_URL}/{username}"
    async with websockets.connect(uri) as ws:
        welcome = await ws.recv()
        print(f"{username}: {welcome}")

        while not game_done_event.is_set():
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                print(f"⏱️ {username} timed out waiting for server message.")
                break

            data = json.loads(msg)
            print(f"{username} got:", data)

            if data.get("game_over"):
                print(f"🏁 Game over! Winner: {data.get('winner')}")
                game_done_event.set()
                break

            if data.get("next_player") == username:
                print(f"🎮 {username}'s turn: {data.get('next_song')}")
                await asyncio.sleep(0.2)
                await ws.send(json.dumps({"type": "guess", "index": guess_index}))


@pytest.mark.asyncio
async def test_game_flow(fastapi_server):
    # Register players
    for name in ["alice", "bob"]:
        res = requests.post(f"{BASE_URL}/register", json={"name": name})
        assert res.status_code == 200, f"Registration failed for {name}"

    game_done_event = asyncio.Event()

    # Start player simulation tasks
    tasks = [
        asyncio.create_task(simulate_player("alice", 0, game_done_event)),
        asyncio.create_task(simulate_player("bob", 0, game_done_event)),
    ]
    await asyncio.sleep(1)  # Give clients time to connect

    # Start the game
    res = requests.post(f"{BASE_URL}/start")
    assert res.status_code == 200, f"Game failed to start: {res.text}"

    # Wait for game to finish or fail
    await asyncio.wait_for(game_done_event.wait(), timeout=30)

    # Clean up
    for t in tasks:
        t.cancel()
