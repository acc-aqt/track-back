"""Browser tests: headless Chromium drives the served Web UI of a Mock server."""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from track_back.music_service.selection import MusicServiceType
from track_back.server.server import Server

STARTUP_TIMEOUT_SECONDS = 10
IDLE_TIMEOUT_SECONDS = 5


@pytest.fixture(scope="session")
def live_server() -> Iterator[tuple[uvicorn.Server, str]]:
    """Run a real TrackBack server with the Mock Music Service on a free port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    app = Server(music_service=MusicServiceType.MOCK).app
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
def _wait_until_the_server_is_idle(
    live_server: tuple[uvicorn.Server, str],
) -> Iterator[None]:
    """Let the server finish handling the closed page before sessions are cleared.

    Autouse fixtures set up before ``page``, so this teardown runs after the page
    closes. Without it, the server could handle the WebSocket disconnect late and
    remove the next test's Game Session of the same name.
    """
    yield
    state = live_server[0].server_state
    deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS
    while state.connections or state.tasks:
        if time.monotonic() > deadline:
            pytest.fail("The TrackBack server still handled requests after the test")
        time.sleep(0.02)
