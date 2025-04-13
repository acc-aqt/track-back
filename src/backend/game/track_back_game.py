"""Contains the TrackBackGame class that implements the game logic."""

from itertools import pairwise

from backend.music_service.abstract_adapter import AbstractMusicServiceAdapter

from .song import Song
from .user import User


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

    def start_game(self):
        self.round_counter = 1
        self.running = True

    def get_current_player(self) -> User:
        return self.users[self.current_turn_index]

    def get_current_song(self) -> Song:
        return self.music_service.current_song()

    def process_turn(self, username: str, insert_index: int) -> dict:
        if not self.running:
            return {"error": "Game not running."}

        player = self.get_current_player()
        if player.name != username:
            return {"error": f"It is not {username}'s turn."}

        current_song = self.get_current_song()
        print(
            f"Current song (bfore verify): {current_song.title} ({current_song.release_year})"
        )

        if self.verify_choice(player.song_list, insert_index, current_song):
            player.add_song(insert_index, current_song)
            print(f"Added song to {player.name} list")
            player.print_song_list()
            print(
                f"serialized song list: {self._serialize_song_list(player.song_list)}"
            )
            result = {
                "result": "correct",
                "message": f"✅ Correct! Song was {current_song.title} ({current_song.release_year})",
            }
        else:
            result = {
                "result": "wrong",
                "message": f"❌ Wrong! Song was {current_song.title} ({current_song.release_year})",
            }
        result["round_counter"] = self.round_counter
        result["current_turn_index"] = self.current_turn_index
        if len(player.song_list) >= self.target_song_count:
            self.running = False
            self.winner = player
            result["game_over"] = True
            result["winner"] = player.name
            result["song_list"] = self._serialize_song_list(player.song_list)
            return result

        result["song_list"] = self._serialize_song_list(player.song_list)

        # Freeze current player before advancing
        result["player"] = player.name

        self._advance_turn()
        self.music_service.next_track()
        current_song = self.get_current_song()
        print(
            f"Current song (after verify): {current_song.title} ({current_song.release_year})"
        )

        result["next_player"] = self.get_current_player().name
        result["next_song"] = (
            f"{self.get_current_song().title} - {self.get_current_song().release_year}"
        )

        return result

    def _advance_turn(self):
        self.round_counter += 1
        self.current_turn_index = (self.current_turn_index + 1) % len(
            self.users
        )

    @staticmethod
    def verify_choice(
        song_list: list[Song], index: int, selected_song: Song
    ) -> bool:
        """Return True if the new song list would be sorted by release year."""
        potential_list = song_list.copy()
        potential_list.insert(index, selected_song)

        return TrackBackGame._is_sorted_by_release_year(potential_list)

    @staticmethod
    def _serialize_song_list(song_list: list[Song]) -> list[dict]:
        return [TrackBackGame._serialize_song(song) for song in song_list]

    @staticmethod
    def _serialize_song(song: Song) -> dict:
        return {
            "title": song.title,
            "artist": song.artist,
            "release_year": song.release_year,
        }

    @staticmethod
    def _is_sorted_by_release_year(song_list: list[Song]) -> bool:
        return all(
            earlier.release_year <= later.release_year
            for earlier, later in pairwise(song_list)
        )

    def is_game_over(self) -> bool:
        return not self.running
