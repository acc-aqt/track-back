from game.game_logic import GameLogic
from game.user import User
from music_service.mock import MockMusicService


def _two_player_game() -> tuple[GameLogic, User, User]:
    game = GameLogic(target_song_count=3, music_service=MockMusicService())
    alice = User("alice")
    bob = User("bob")
    game.start_game(users=[alice, bob])
    return game, alice, bob


def test_round_does_not_advance_when_no_active_players_remain() -> None:
    game, alice, _bob = _two_player_game()

    assert game.round.player_left("alice") is False
    assert game.round.player_left("bob") is False

    alice.is_active = True
    game.handle_player_turn("alice", 0)
    assert [song.title for song in alice.song_list] == ["Yesterday"]


def test_round_advances_when_last_owed_player_leaves() -> None:
    game, alice, _bob = _two_player_game()

    game.handle_player_turn("alice", 0)
    assert game.round.player_left("bob") is True

    game.handle_player_turn("alice", 1)
    assert [song.title for song in alice.song_list] == [
        "Yesterday",
        "Bohemian Rhapsody",
    ]
