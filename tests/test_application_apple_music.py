"""Full application/game tests for integration of Apple Music."""

import builtins
from unittest.mock import patch

import pytest

from game.track_back_game import TrackBackGame
from game.user import User
from music_service.apple_music import AppleMusicAdapter


@pytest.mark.skipif(
    not AppleMusicAdapter.running_on_macos(), reason="Test only runs on macOS"
)
@pytest.mark.skipif(
    not AppleMusicAdapter.music_app_is_running(),
    reason="Apple Music is not running",
)
def test_full_game_one_round() -> None:
    """Test a full game with one round."""
    users = [User("Elton"), User("John")]

    music_service = AppleMusicAdapter()
    game = TrackBackGame(
        target_song_count=1,
        music_service=music_service,
        users=users,
    )
    # Simulate one user input: "0" to insert at start
    with patch.object(builtins, "input", side_effect=["0"]):
        game.run()

    winner = game.winner

    assert winner == users[0]  # First user instantly wins after first input
    assert len(winner.song_list) == 1
