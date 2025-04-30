import pytest
from game.user import User
from music_service.mock import DummyMusicService
from game.game_logic import GameLogic
from game.strategies.factory import GameStrategyEnum


@pytest.fixture(params=[GameStrategyEnum.SEQUENTIAL, GameStrategyEnum.SIMULTANEOUS])
def test_env(request):
    game = GameLogic(
        target_song_count=2, music_service=DummyMusicService(), game_strategy_enum=request.param
    )

    return game


def test_single_player_game(test_env):
    game = test_env
    assert game.running is False

    test_user = User("testuser")
    game.start_game(users=[test_user])
    assert game.is_game_over() is False
    assert len(test_user.song_list) == 0

    # user makes first guess -> correct
    game.handle_player_turn(test_user.name, 0)
    assert len(test_user.song_list) == 1
    assert game.is_game_over() is False

    # user makes wrong guess (songs from mock are delived with increasing release year)
    game.handle_player_turn(test_user.name, 0)
    assert len(test_user.song_list) == 1
    assert game.is_game_over() is False
    assert game.winner is None


    # user makes correct guess (songs from mock are delived with increasing release year)
    game.handle_player_turn(test_user.name, 1)
    assert len(test_user.song_list) == 2
    assert game.is_game_over() is True
    assert game.winner == test_user