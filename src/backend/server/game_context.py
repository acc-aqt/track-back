"""Contains the GameContext class, which holds the shared game state."""

from fastapi import WebSocket

from backend.game.track_back_game import TrackBackGame
from backend.game.user import User
from backend.music_service.abstract_adapter import AbstractMusicServiceAdapter


class GameContext:
    """Holds the shared game state across requests and WebSocket sessions."""

    def __init__(
        self,
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
    ) -> None:
        self.target_song_count = target_song_count
        self.music_service = music_service
        self.game: TrackBackGame | None = None
        self.connected_users: dict[str, WebSocket] = {}
        self.registered_users: dict[str, User] = {}
        self.first_player: User | None = None

    def reset(self) -> None:
        """Reset the game context to its initial state."""
        self.game = None
        self.connected_users.clear()
        self.registered_users.clear()
        self.first_player = None
