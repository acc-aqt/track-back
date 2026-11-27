"""Contains the GameLogic class that implements the game logic."""

import logging
from dataclasses import dataclass
from itertools import pairwise

from track_back.game.errors import MusicPlaybackError
from track_back.game.player import Player
from track_back.game.simultaneous_round import SimultaneousRound
from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.error import MusicServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GuessResult:
    """The outcome of an accepted Guess.

    ``player`` is the guessing Player, whose Timeline already includes the Song
    if the Guess was correct. ``winner`` is set when this Guess won the game.
    """

    player: Player
    correct: bool
    song: Song
    position: int
    other_players: list[Player]
    winner: Player | None = None
    round_complete: bool = False


@dataclass(frozen=True)
class GuessRejected:
    """A Guess the game did not accept, and why."""

    reason: str


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
        self.round_song: Song | None = None

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
        self._read_round_song()

    def handle_guess(
        self, username: str, insert_index: int
    ) -> GuessResult | GuessRejected:
        """Handle a player's guess of the current song."""
        if not self.running:
            return GuessRejected("Game not running.")
        if self.round_tracker.has_guessed(username):
            return GuessRejected(f"{username} has already guessed this song.")

        player = next(player for player in self.players if player.name == username)
        if not 0 <= insert_index <= len(player.timeline):
            return GuessRejected(f"Invalid position {insert_index}.")

        song = self._round_song()
        correct = self.verify_choice(player.timeline, insert_index, song)
        if correct:
            player.add_to_timeline(insert_index, song)
        other_players = [other for other in self.players if other != player]

        if len(player.timeline) >= self.target_song_count:
            self.running = False
            self.winner = player
            return GuessResult(
                player, correct, song, insert_index, other_players, winner=player
            )

        self.round_tracker.record_guess(username)
        return GuessResult(
            player,
            correct,
            song,
            insert_index,
            other_players,
            round_complete=self._advance_round_if_complete(),
        )

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
        self._read_round_song()
        return True

    def _read_round_song(self) -> None:
        """Read the Song of the Round that just started, or leave it to the first Guess."""
        try:
            self.round_song = self.music_service.current_song()
        except MusicServiceError:
            logger.warning("Could not read the Round's Song; retrying on a Guess.")
            self.round_song = None

    def _round_song(self) -> Song:
        """Return the Round's Song, reading it if the Round's start could not."""
        if self.round_song is None:
            self.round_song = self.music_service.current_song()
        return self.round_song

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
