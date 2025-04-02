"""Tests for the TrackBackGame class."""

import unittest

from src.game.song import Song
from src.game.track_back_game import TrackBackGame, TrackBackGameException
from src.game.user import User


class TestCorrectChoice(unittest.TestCase):
    """Tests for the _correct_choice method of the TrackBackGame class."""

    def setUp(self):
        self.game = TrackBackGame(target_song_count=0, music_provider=None)
        self.song_70s = Song("Bohemian Rhapsody", "Queen", 1975)
        self.song_80s = Song("Hier kommt Alex", "Die Toten Hosen", 1988)
        self.song_90s = Song("Scatman (ski-ba-bop-ba-dop-bop)", "Scatman John", 1995)

    def test_empty_list_returns_true(self):
        """Test that an empty list always returns True."""
        self.assertTrue(self.game._correct_choice([], 0, self.song_90s))

    def test_insert_at_start_correct(self):
        """Test that a song can be inserted at the start of the list."""
        song_list = [self.song_80s]
        new_song = self.song_70s
        self.assertTrue(self.game._correct_choice(song_list, 0, new_song))

    def test_insert_at_start_incorrect(self):
        """Test that a song cannot be inserted at the start of the list."""
        song_list = [self.song_80s]
        new_song = self.song_90s
        self.assertFalse(self.game._correct_choice(song_list, 0, new_song))

    def test_insert_at_end_correct(self):
        """Test that a song can be inserted at the end of the list."""
        song_list = [self.song_80s]
        new_song = self.song_90s
        self.assertTrue(self.game._correct_choice(song_list, -1, new_song))
        self.assertTrue(
            self.game._correct_choice(song_list, 1, new_song)
        )  # len(song_list) == 1

    def test_insert_at_end_incorrect(self):
        """Test that a song cannot be inserted at the end of the list."""
        song_list = [self.song_80s]
        new_song = self.song_70s
        self.assertFalse(self.game._correct_choice(song_list, -1, new_song))

    def test_insert_in_middle_correct(self):
        """Test that a song can be inserted in the middle of the list."""
        song_list = [self.song_70s, self.song_90s]
        new_song = self.song_80s
        self.assertTrue(self.game._correct_choice(song_list, 1, new_song))

    def test_insert_in_middle_equal_years_correct(self):
        """Test that a song can be inserted in the middle of the list if a neighboring year is equal."""
        song_list = [self.song_70s, self.song_90s]
        new_song = self.song_70s
        self.assertTrue(self.game._correct_choice(song_list, 1, new_song))

    def test_insert_in_middle_incorrect(self):
        """Test that a song cannot be inserted in the middle of the list."""
        song_list = [self.song_70s, self.song_80s]
        new_song = self.song_90s
        self.assertFalse(self.game._correct_choice(song_list, 1, new_song))

    def test_invalid_index_raises_exception(self):
        """Test that an invalid index raises an exception."""
        song_list = [self.song_70s]
        new_song = self.song_80s
        with self.assertRaises(TrackBackGameException):
            self.game._correct_choice(song_list, 5, new_song)
