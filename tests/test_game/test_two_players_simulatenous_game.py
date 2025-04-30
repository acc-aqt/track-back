from game.user import User
from music_service.mock import DummyMusicService
from game.game_logic import GameLogic
from game.strategies.factory import GameStrategyEnum


def test_two_players_simulteneous_game():
    game = GameLogic(
        target_song_count=3,
        music_service=DummyMusicService(),
        game_strategy_enum=GameStrategyEnum.SIMULTANEOUS,
    )
    assert game.running is False

    player1 = User("player1")
    player2 = User("player2")

    game.start_game(users=[player1, player2])
    assert game.is_game_over() is False
    assert len(player1.song_list) == 0
    assert len(player2.song_list) == 0

    # Player1: Send the first guess
    game.handle_player_turn(player1.name, 0)
    assert len(player1.song_list) == 1
    assert len(player2.song_list) == 0
    assert game.is_game_over() is False

    # Player1: Make another guess --> not his turn
    game.handle_player_turn(player1.name, 1)
    assert len(player1.song_list) == 1
    assert len(player2.song_list) == 0
    assert game.is_game_over() is False

    # Player2: Send his first guess
    game.handle_player_turn(player2.name, 0)
    assert len(player1.song_list) == 1
    assert len(player2.song_list) == 1
    assert game.is_game_over() is False

    # new round

    # Player2: Make another, correct guess
    game.handle_player_turn(player2.name, 1)
    assert len(player1.song_list) == 1
    assert len(player2.song_list) == 2
    assert game.is_game_over() is False

    # Player1: Make correct guess
    game.handle_player_turn(player1.name, 1)
    assert len(player1.song_list) == 2
    assert len(player2.song_list) == 2
    assert game.is_game_over() is False
    assert game.winner is None

    # new round

    # Player1: Make wrong guess
    game.handle_player_turn(player1.name, 0)
    assert len(player1.song_list) == 2
    assert len(player2.song_list) == 2
    assert game.is_game_over() is False
    assert game.winner == None

    # Player2: Make correct guess
    game.handle_player_turn(player2.name, 2)
    assert len(player1.song_list) == 2
    assert len(player2.song_list) == 3
    assert game.is_game_over() is True
    assert game.winner == player2
