"""Contains the GameContext class, which holds the shared game state."""

from fastapi import WebSocket

from game.user import User
from music_service.abstract_adapter import AbstractMusicServiceAdapter


class GameContext:
    """Holds the shared game state across requests and WebSocket sessions."""

    def __init__(
        self,
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
    ) -> None:
        self.target_song_count = target_song_count
        self.music_service = music_service

        self.connected_users: dict[str, WebSocket] = {}
        self.registered_users: dict[str, User] = {}

        self.first_player: str | None = None
