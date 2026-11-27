"""Contains the GameLogic class that implements the game logic."""

from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from track_back.game.errors import MusicPlaybackError
from track_back.game.messages import MessageType
from track_back.game.player import Player
from track_back.game.simultaneous_round import SimultaneousRound
from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.error import MusicServiceError


@dataclass(frozen=True)
class GuessResult:
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
        self.players: list[Player] = []

        self.music_service = music_service

        self.running = False
        self.winner: Player | None = None

    def start_game(self, players: list[Player]) -> None:
        """Start the game with the given players."""
        try:
            self.music_service.start_playback()
        except MusicServiceError as e:
            raise MusicPlaybackError(self.music_service.service_name) from e
        self.players = players
        self.running = True

    def handle_guess(self, username: str, insert_index: int) -> GuessResult:
        """Handle a player's guess of the current song."""
        if not self.running:
            return _error("Game not running.")
        if self.round_tracker.has_guessed(username):
            return _error(f"{username} has already guessed this song.")

        player = next(player for player in self.players if player.name == username)
        if not 0 <= insert_index <= len(player.timeline):
            return _error(f"Invalid position {insert_index}.")

        payload: dict[str, Any] = {}

        current_song = self.music_service.current_song()

        payload["type"] = MessageType.GUESS_RESULT
        payload["player"] = username

        if self.verify_choice(player.timeline, insert_index, current_song):
            player.add_to_timeline(insert_index, current_song)
            payload["result"] = "correct"
        else:
            payload["result"] = "wrong"
        payload["message"] = f"Song was {current_song}."

        payload["other_players"] = [
            other.serialize() for other in self.players if other != player
        ]
        payload["last_index"] = str(insert_index)
        payload["last_song"] = current_song.serialize()
        payload["song_list"] = [song.serialize() for song in player.timeline]

        if len(player.timeline) >= self.target_song_count:
            self.running = False
            self.winner = player
            payload["game_over"] = True
            payload["winner"] = player.name
            return GuessResult(payload)

        payload["game_over"] = False
        payload["winner"] = ""

        self.round_tracker.record_guess(username)
        return GuessResult(payload, round_complete=self._advance_round_if_complete())

    def player_disconnected(self, username: str) -> bool:
        """Stop waiting for a departed player; return True if the round advanced."""
        if player := self.get_player(username):
            player.is_connected = False
        return self._advance_round_if_complete()

    def player_rejoined(self, username: str) -> None:
        """Count a rejoining player as connected again."""
        if player := self.get_player(username):
            player.is_connected = True

    def _advance_round_if_complete(self) -> bool:
        connected_usernames = {
            player.name for player in self.players if player.is_connected
        }
        if not self.running or not self.round_tracker.is_complete(connected_usernames):
            return False
        self.music_service.next_track()
        self.round_tracker.start_next()
        return True

    @staticmethod
    def verify_choice(timeline: list[Song], index: int, selected_song: Song) -> bool:
        """Return True if the timeline with the song added would be sorted by release year."""
        potential_timeline = timeline.copy()
        potential_timeline.insert(index, selected_song)

        return GameLogic._is_sorted_by_release_year(potential_timeline)

    @staticmethod
    def _is_sorted_by_release_year(songs: list[Song]) -> bool:
        return all(
            earlier.release_year <= later.release_year
            for earlier, later in pairwise(songs)
        )

    def is_game_over(self) -> bool:
        """Return True if the game is over."""
        return not self.running

    def get_player(self, username: str) -> Player | None:
        """Return the player with the given username."""
        for player in self.players:
            if player.name == username:
                return player
        return None

    def owes_guess(self, username: str) -> bool:
        """Return True if the player still has to guess the current song."""
        return (
            self.running
            and self.get_player(username) is not None
            and not self.round_tracker.has_guessed(username)
        )

    def players_owing_guess(self) -> list[Player]:
        """Return the players who still have to guess the current song."""
        return [player for player in self.players if self.owes_guess(player.name)]

    def disconnected_player_names(self) -> list[str]:
        """Return the names of players who are not connected."""
        return [player.name for player in self.players if not player.is_connected]

    def has_disconnected_players(self) -> bool:
        """Return True if any player is not connected."""
        return bool(self.disconnected_player_names())


def _error(message: str) -> GuessResult:
    return GuessResult({"type": MessageType.ERROR, "message": message})
