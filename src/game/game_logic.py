"""Contains the GameLogic class that implements the game logic."""

from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from game.errors import MusicPlaybackError
from game.messages import MessageType
from game.simultaneous_round import SimultaneousRound
from game.song import Song
from game.user import User
from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.error import MusicServiceError


@dataclass(frozen=True)
class TurnResult:
    """The message for the guessing player and whether the guess ended the round."""

    message: dict[str, Any]
    round_complete: bool = False


class GameLogic:
    """Implements the game logic."""

    def __init__(
        self,
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
    ) -> None:
        self.target_song_count = target_song_count
        self.round_tracker = SimultaneousRound()
        self.users: list[User] = []

        self.music_service = music_service

        self.running = False
        self.winner: User | None = None

    def start_game(self, users: list[User]) -> None:
        """Start the game with the given users."""
        try:
            self.music_service.start_playback()
        except MusicServiceError as e:
            raise MusicPlaybackError(self.music_service.service_name) from e
        self.users = users
        self.running = True

    def handle_player_turn(self, username: str, insert_index: int) -> TurnResult:
        """Handle a player's turn."""
        if not self.running:
            return _error("Game not running.")
        if self.round_tracker.has_guessed(username):
            return _error(f"{username} has already guessed this song.")

        player = next(user for user in self.users if user.name == username)
        if not 0 <= insert_index <= len(player.song_list):
            return _error(f"Invalid position {insert_index}.")

        payload: dict[str, Any] = {}

        current_song = self.music_service.current_song()

        payload["type"] = MessageType.GUESS_RESULT
        payload["player"] = username

        if self.verify_choice(player.song_list, insert_index, current_song):
            player.add_song(insert_index, current_song)
            payload["result"] = "correct"
        else:
            payload["result"] = "wrong"
        payload["message"] = f"Song was {current_song}."

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
            return TurnResult(payload)

        payload["game_over"] = False
        payload["winner"] = ""

        self.round_tracker.record_guess(username)
        return TurnResult(payload, round_complete=self._advance_round_if_complete())

    def player_left(self, username: str) -> bool:
        """Stop waiting for a departed player; return True if the round advanced."""
        if user := self.get_user(username):
            user.is_active = False
        return self._advance_round_if_complete()

    def player_returned(self, username: str) -> None:
        """Count a returning member as active again."""
        if user := self.get_user(username):
            user.is_active = True

    def _advance_round_if_complete(self) -> bool:
        active_usernames = {user.name for user in self.users if user.is_active}
        if not self.running or not self.round_tracker.is_complete(active_usernames):
            return False
        self.music_service.next_track()
        self.round_tracker.start_next()
        return True

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

    def get_user(self, username: str) -> User | None:
        """Return the user with the given username."""
        for user in self.users:
            if user.name == username:
                return user
        return None

    def owes_guess(self, username: str) -> bool:
        """Return True if the member still has to guess the current song."""
        return (
            self.running
            and self.get_user(username) is not None
            and not self.round_tracker.has_guessed(username)
        )

    def players_owed_card(self) -> list[User]:
        """Return the members who still have to guess the current song."""
        return [user for user in self.users if self.owes_guess(user.name)]

    def inactive_member_names(self) -> list[str]:
        """Return the names of members who are not connected."""
        return [user.name for user in self.users if not user.is_active]

    def has_inactive_members(self) -> bool:
        """Return True if any member is not connected."""
        return bool(self.inactive_member_names())


def _error(message: str) -> TurnResult:
    return TurnResult({"type": MessageType.ERROR, "message": message})
