"""Full application/game tests for integration of Apple Music."""

import pytest

from game.game_logic import GameLogic
from game.user import User
from music_service.apple_music import AppleMusicAdapter


@pytest.mark.skipif(not AppleMusicAdapter.running_on_macos(), reason="Test only runs on macOS")
@pytest.mark.skipif(
    not AppleMusicAdapter.music_app_is_running(),
    reason="Apple Music is not running",
)
def test_full_game_one_round() -> None:
    """Test a full game with one round."""
    user_1 = User("Elton")
    user_2 = User("John")

    music_service = AppleMusicAdapter()
    game = GameLogic(
        target_song_count=1,
        music_service=music_service,
    )
    game.start_game(users=[user_1, user_2])
    # Simulate one user input: "0" to insert at start

    game.handle_player_turn("Elton", 0)

    assert game.is_game_over() == True

    winner = game.winner

    assert winner == user_1  # First user instantly wins after first input
    assert len(winner.song_list) == 1
