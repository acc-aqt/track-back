"""Contains the TrackBackGame class that implements the game logic."""

from itertools import pairwise
from typing import Any

from game.song import Song
from game.user import User
from music_service.abstract_adapter import AbstractMusicServiceAdapter


class TrackBackGameError(Exception):
    """Base class for exceptions in this module."""


class TrackBackGame:
    """Implements the game logic."""

    def __init__(
        self,
        users: list[User],
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
    ) -> None:
        self.music_service = music_service
        self.target_song_count = target_song_count
        self.users = users
        self.round_counter = 0
        self.winner: User | None = None

        self.current_turn_index = 0
        self.running = False

    def start_game(self) -> None:
        """Start the game."""
        self.round_counter = 1
        self.running = True

    def get_current_player(self) -> User:
        """Get the current player."""
        return self.users[self.current_turn_index]

    def handle_player_turn(self, username: str, insert_index: int) -> dict[str, Any]:
        """Handle a player's turn."""
        payload: dict[str, Any] = {}
        if not self.running:
            payload["type"] = "error"
            payload["message"] = "⚠️ Game not running."
            return payload

        player = self.get_current_player()
        if player.name != username:
            payload["type"] = "error"
            payload["message"] = f"It is not {username}'s turn."
            return payload

        current_song = self.music_service.current_song()

        payload["type"] = "guess_result"
        payload["player"] = username
        if self.verify_choice(player.song_list, insert_index, current_song):
            player.add_song(insert_index, current_song)
            payload["result"] = "correct"
            payload["message"] = f"✅ Correct! Song was {current_song}."
        else:
            payload["result"] = "wrong"
            payload["message"] = f"❌ Wrong! Song was {current_song}."

        payload["other_players"] = [
            user.serialize() for user in self.users if user != player
        ]
        payload["last_index"] = str(insert_index)
        payload["last_song"] = current_song.serialize()
        payload["round_counter"] = str(self.round_counter)
        payload["current_turn_index"] = str(self.current_turn_index)
        payload["song_list"] = [song.serialize() for song in player.song_list]

        if len(player.song_list) >= self.target_song_count:
            self.running = False
            self.winner = player
            payload["game_over"] = True
            payload["winner"] = player.name
            return payload

        payload["game_over"] = False
        payload["winner"] = ""

        # Freeze current player before advancing
        payload["player"] = player.name
        self._advance_turn()
        self.music_service.next_track()

        payload["next_player"] = self.get_current_player().name

        return payload

    def _advance_turn(self) -> None:
        self.round_counter += 1
        self.current_turn_index = (self.current_turn_index + 1) % len(self.users)

    @staticmethod
    def verify_choice(song_list: list[Song], index: int, selected_song: Song) -> bool:
        """Return True if the new song list would be sorted by release year."""
        potential_list = song_list.copy()
        potential_list.insert(index, selected_song)

        return TrackBackGame._is_sorted_by_release_year(potential_list)

    @staticmethod
    def _is_sorted_by_release_year(song_list: list[Song]) -> bool:
        return all(
            earlier.release_year <= later.release_year
            for earlier, later in pairwise(song_list)
        )

    def is_game_over(self) -> bool:
        """Return True if the game is over."""
        return not self.running
