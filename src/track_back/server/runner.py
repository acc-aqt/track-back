"""Run the TrackBack app with Uvicorn: SSL, the startup hint and ready callbacks."""

import logging
import os
import socket
from collections.abc import Callable

import uvicorn
from fastapi import FastAPI

from track_back.server import network

logger = logging.getLogger(__name__)


def startup_hint(port: int, *, use_ssl: bool, lan_addresses: list[str]) -> str:
    """Tell the host which URLs open the Web UI.

    Parameters
    ----------
    port : int
        The port the server listens on.
    use_ssl : bool
        Whether the server serves HTTPS.
    lan_addresses : list[str]
        The addresses other devices can reach this machine on.

    Returns
    -------
    str
        One sentence naming the ``localhost`` URL and one URL per LAN address.
    """
    hint = f"Open {base_url('localhost', port, use_ssl=use_ssl)} on this machine"
    if not lan_addresses:
        return f"{hint}."
    lan_urls = " or ".join(
        base_url(address, port, use_ssl=use_ssl) for address in lan_addresses
    )
    return f"{hint}, or {lan_urls} on other devices."


def base_url(host: str, port: int, *, use_ssl: bool) -> str:
    """Build the server's URL on ``host``, without a trailing slash."""
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


def _ssl_files() -> tuple[str, str] | None:
    keyfile = os.getenv("SSL_KEYFILE")
    certfile = os.getenv("SSL_CERTFILE")
    if keyfile and certfile:
        return keyfile, certfile
    return None


def uses_ssl() -> bool:
    """Tell whether the SSL config asks the server to serve HTTPS.

    Returns
    -------
    bool
        True when both ``SSL_KEYFILE`` and ``SSL_CERTFILE`` are set.
    """
    return _ssl_files() is not None


class _ReadyNotifyingServer(uvicorn.Server):
    """Uvicorn server that runs callbacks once it accepts connections."""

    def __init__(
        self, config: uvicorn.Config, ready_callbacks: list[Callable[[], None]]
    ) -> None:
        super().__init__(config)
        self._ready_callbacks = ready_callbacks

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if not self.started:
            return
        for callback in self._ready_callbacks:
            callback()


def serve(app: FastAPI, port: int, ready_callbacks: list[Callable[[], None]]) -> None:
    """Print where to open the Web UI, then serve the app until it stops.

    Parameters
    ----------
    app : FastAPI
        The app to serve on all interfaces.
    port : int
        The port to listen on.
    ready_callbacks : list[Callable[[], None]]
        Run once the server accepts connections.
    """
    ssl_files = _ssl_files()
    lan_addresses = network.lan_ipv4_addresses_or_empty()
    print(
        startup_hint(port, use_ssl=ssl_files is not None, lan_addresses=lan_addresses)
    )

    ssl_keyfile, ssl_certfile = ssl_files or (None, None)
    logger.info("Running server %s SSL.", "with" if ssl_files else "without")
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",  # noqa: S104
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )
    _ReadyNotifyingServer(uvicorn_config, ready_callbacks).run()
