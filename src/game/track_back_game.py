"""Contains the TrackBackGame class that implements the game logic."""

from enum import Enum
from itertools import pairwise
from typing import Any

from game.song import Song
from game.user import User
from music_service.abstract_adapter import AbstractMusicServiceAdapter


class GameMode(Enum):
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"


class TrackBackGameError(Exception):
    """Base class for exceptions in this module."""


class TrackBackGame:
    """Implements the game logic."""

    def __init__(
        self,
        users: list[User],
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
        game_mode: GameMode = GameMode.SEQUENTIAL,
    ) -> None:
        self.music_service = music_service
        self.target_song_count = target_song_count
        self.game_mode = game_mode
        self.users = users

        self.running = False
        self.winner: User | None = None

        self.current_turn_index = 0
        self.users_already_guessed: set[str] = set()

    def start_game(self) -> None:
        """Start the game."""
        self.running = True

    # only for sequential mode?
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
        
        if self.game_mode == GameMode.SEQUENTIAL:
            player = self.get_current_player()
            if player.name != username:
                payload["type"] = "error"
                payload["message"] = f"It is not {username}'s turn."
                return payload
        elif self.game_mode == GameMode.SEQUENTIAL:
            if username in self.users_already_guessed:
                payload["type"] = "error"
                payload["message"] = f"⚠️ {username} has already guessed this song."
                return payload
            
        else:
            raise Exception("Invalid game mode")
            

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
        if self.game_mode == GameMode.SEQUENTIAL:
            self.current_turn_index = (self.current_turn_index + 1) % len(self.users)
            self.music_service.next_track()
            payload["next_player"] = self.get_current_player().name
        elif self.game_mode == GameMode.SIMULTANEOUS:
            self.users_already_guessed.add(username)
            payload["next_player"] = None
            if len(self.users_already_guessed) == len(self.users):
                self.users_already_guessed.clear()
                self.music_service.next_track()

        return payload

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
