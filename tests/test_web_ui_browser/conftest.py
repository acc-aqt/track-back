"""Browser tests: headless Chromium drives the served Web UI of a Mock server."""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from track_back.music_service.selection import MusicServiceType
from track_back.server.game_sessions import GameSessionManager
from track_back.server.server import Server

STARTUP_TIMEOUT_SECONDS = 10
IDLE_TIMEOUT_SECONDS = 5


@pytest.fixture(scope="session")
def live_game_sessions() -> GameSessionManager:
    return GameSessionManager()


@pytest.fixture(scope="session")
def live_server(
    live_game_sessions: GameSessionManager,
) -> Iterator[tuple[uvicorn.Server, str]]:
    """Run a real TrackBack server with the Mock Music Service on a free port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    app = Server(
        music_service=MusicServiceType.MOCK, game_sessions=live_game_sessions
    ).app
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
    thread.start()
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            pytest.fail("The TrackBack server for the browser tests did not start")
        time.sleep(0.05)
    yield server, f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()
    sock.close()


@pytest.fixture(scope="session")
def base_url(live_server: tuple[uvicorn.Server, str]) -> str:
    return live_server[1]


@pytest.fixture(autouse=True)
def _start_each_test_without_game_sessions(
    live_server: tuple[uvicorn.Server, str],
    live_game_sessions: GameSessionManager,
) -> Iterator[None]:
    """Remove the test's Game Sessions once the server has handled the closed page.

    Autouse fixtures set up before ``page``, so this teardown runs after the page
    closes. Without the wait, the server could handle the WebSocket disconnect late
    and remove the next test's Game Session of the same name.
    """
    yield
    state = live_server[0].server_state
    deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS
    while state.connections or state.tasks:
        if time.monotonic() > deadline:
            pytest.fail("The TrackBack server still handled requests after the test")
        time.sleep(0.02)
    live_game_sessions.sessions.clear()
