"""Tests for the TrackBackGame class."""

import pytest

from game.song import Song
from game.track_back_game import TrackBackGame, TrackBackGameError
from game.user import User

song_70s = Song("Bohemian Rhapsody", "Queen", 1975)
song_80s = Song("Hier kommt Alex", "Die Toten Hosen", 1988)
song_90s = Song("Scatman (ski-ba-bop-ba-dop-bop)", "Scatman John", 1995)


@pytest.mark.parametrize(
    ("song_list", "index", "selected_song", "expected_result"),
    [
        (
            # "empty_song_list",
            [],
            0,
            song_70s,
            True,
        ),
        (
            # "first_song_correct",
            [song_80s],
            0,
            song_70s,
            True,
        ),
        (
            # "first_song_incorrect",
            [song_80s],
            0,
            song_90s,
            False,
        ),
        (
            # "last_song_correct_neg_index",
            [song_80s],
            -1,
            song_90s,
            True,
        ),
        (
            # "last_song_correct_len_index",
            [song_80s],
            1,
            song_90s,
            True,
        ),
        (
            # "last_song_incorrect",
            [song_80s],
            -1,
            song_70s,
            False,
        ),
        (
            # "middle_song_correct",
            [
                song_70s,
                song_90s,
            ],
            1,
            song_80s,
            True,
        ),
        (
            # "middle_song_incorrect_lower_bound",
            [
                song_80s,
                song_90s,
            ],
            1,
            song_70s,
            False,
        ),
        (
            # "middle_song_incorrect_upper_bound",
            [
                song_70s,
                song_80s,
            ],
            1,
            song_90s,
            False,
        ),
    ],
)
def test_correct_choice(
    song_list: list[User],
    index: int,
    selected_song: Song,
    expected_result: bool,
) -> None:
    """Test _correct_choice with various scenarios."""
    # Act
    result = TrackBackGame.verify_choice(None, song_list, index, selected_song)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    ("song_list", "index", "selected_song"),
    [
        (
            # "invalid_index_negative",
            [song_80s],
            -2,
            song_90s,
        ),
        (
            # "invalid_index_positive",
            [song_80s],
            2,
            song_90s,
        ),
    ],
)
def test_correct_choice_invalid_index(
    song_list: list[Song], index: int, selected_song: Song
) -> None:
    """Test _correct_choice with invalid index raises TrackBackGameError."""
    # Act & Assert
    with pytest.raises(TrackBackGameError):
        TrackBackGame.verify_choice(None, song_list, index, selected_song)
