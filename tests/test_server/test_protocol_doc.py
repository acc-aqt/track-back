"""Tests that the WebSocket protocol document keeps up with the code."""

from pathlib import Path

import pytest

from track_back.game.messages import MessageType
from track_back.server.server import CLIENT_MESSAGE_HANDLERS

PROTOCOL_DOC = Path(__file__).parents[2] / "docs" / "websocket-protocol.md"


@pytest.mark.parametrize("message_type", list(MessageType))
def test_every_server_message_type_is_documented(message_type: MessageType) -> None:
    assert f"`{message_type}`" in PROTOCOL_DOC.read_text()


@pytest.mark.parametrize("message_type", list(CLIENT_MESSAGE_HANDLERS))
def test_every_client_message_type_is_documented(message_type: str) -> None:
    assert f"`{message_type}`" in PROTOCOL_DOC.read_text()
