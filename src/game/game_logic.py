"""Contains the TrackBackGame class that implements the game logic."""

from itertools import pairwise
from typing import Any

from fastapi import HTTPException

from game.song import Song
from game.strategies.factory import GameStrategyEnum, GameStrategyFactory
from game.user import User
from music_service.error import MusicServiceError
from music_service.spotify import current_adapter


class GameLogic:
    """Implements the game logic."""

    def __init__(
        self,
        target_song_count: int,
        game_strategy_enum: GameStrategyEnum = GameStrategyEnum.SIMULTANEOUS,
    ) -> None:
        self.music_service = None
        self.target_song_count = target_song_count
        self.strategy = GameStrategyFactory.create_game_strategy(
            game_strategy_enum, self
        )
        self.users: list[User] = []

        self.running = False
        self.winner: User | None = None

    def start_game(self, users: list[User]) -> None:
        """Start the game."""
        from music_service.spotify import current_adapter  # ensure fresh import
        if current_adapter is None:
            raise HTTPException(status_code=400, detail="Spotify not authenticated yet.")
        
        self.music_service = current_adapter
        try:
            self.music_service.start_playback()
        except MusicServiceError as e:
            raise HTTPException(status_code=500, detail="Failed to play music") from e
            try:
                self.music_service.start_playback()
            except MusicServiceError as e:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to play music",
                ) from e
            self.users = users
            self.running = True

    def handle_player_turn(self, username: str, insert_index: int) -> dict[str, Any]:
        """Handle a player's turn."""
        payload: dict[str, Any] = {}
        if not self.running:
            payload["type"] = "error"
            payload["message"] = "Game not running."
            return payload

        validation = self.strategy.validate_turn(username)
        if validation:
            return validation

        player = next(user for user in self.users if user.name == username)
        current_song = self.music_service.current_song()

        payload["type"] = "guess_result"
        payload["player"] = username

        if self.verify_choice(player.song_list, insert_index, current_song):
            player.add_song(insert_index, current_song)
            payload["result"] = "correct"
        else:
            payload["result"] = "wrong"
        payload["message"] = f"Wrong! Song was {current_song}."

        payload["other_players"] = [
            user.serialize() for user in self.users if user != player
        ]
        payload["last_index"] = str(insert_index)
        payload["last_song"] = current_song.serialize()
        payload["song_list"] = [song.serialize() for song in player.song_list]

        if len(player.song_list) >= self.target_song_count:
            self.running = False
            self.winner = player
            payload["game_over"] = True
            payload["winner"] = player.name
            return payload

        payload["game_over"] = False
        payload["winner"] = ""
        payload["player"] = player.name

        progression = self.strategy.handle_turn_progression(username)
        payload.update(progression)

        return payload

    @staticmethod
    def verify_choice(song_list: list[Song], index: int, selected_song: Song) -> bool:
        """Return True if the new song list would be sorted by release year."""
        potential_list = song_list.copy()
        potential_list.insert(index, selected_song)

        return GameLogic._is_sorted_by_release_year(potential_list)

    @staticmethod
    def _is_sorted_by_release_year(song_list: list[Song]) -> bool:
        return all(
            earlier.release_year <= later.release_year
            for earlier, later in pairwise(song_list)
        )

    def is_game_over(self) -> bool:
        """Return True if the game is over."""
        return not self.running
