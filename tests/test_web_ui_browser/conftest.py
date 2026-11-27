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


@pytest.fixture(scope="session")
def base_url() -> Iterator[str]:
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
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()
    sock.close()
