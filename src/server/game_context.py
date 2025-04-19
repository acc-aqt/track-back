"""Contains the GameContext class, which holds the shared game state."""
from fastapi import WebSocket

from game.track_back_game import TrackBackGame
from game.user import User
from game.game_modes import GameMode
from music_service.abstract_adapter import AbstractMusicServiceAdapter


    
class GameContext:
    """Holds the shared game state across requests and WebSocket sessions."""

    def __init__(
        self,
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
        game_mode: GameMode = GameMode.SEQUENTIAL,

    ) -> None:
        self.target_song_count = target_song_count
        self.music_service = music_service
        self.game_mode = game_mode
        self.game: TrackBackGame | None = None

        self.connected_users: dict[str, WebSocket] = {}
        self.registered_users: dict[str, User] = {}

        self.first_player: str | None = None
