import pytest

from track_back.game.game_logic import GameLogic
from track_back.game.player import Player
from track_back.music_service.mock import MockMusicService


@pytest.fixture
def test_env() -> GameLogic:
    game = GameLogic(target_song_count=2, music_service=MockMusicService())

    return game


def test_single_player_game(test_env: GameLogic) -> None:
    game = test_env
    assert game.running is False

    test_player = Player("testplayer")
    game.start_game(players=[test_player])
    assert game.is_game_over() is False
    assert len(test_player.timeline) == 0

    # user makes first guess -> correct
    game.handle_guess(test_player.name, 0)
    assert len(test_player.timeline) == 1
    assert game.is_game_over() is False

    # user makes wrong guess (songs from mock are delived with increasing release year)
    game.handle_guess(test_player.name, 0)
    assert len(test_player.timeline) == 1
    assert game.is_game_over() is False
    assert game.winner is None

    # user makes correct guess (songs from mock are delived with increasing release year)
    game.handle_guess(test_player.name, 1)
    assert len(test_player.timeline) == 2
    assert game.is_game_over() is True
    assert game.winner == test_player
