from track_back.game.game_logic import GameLogic
from track_back.game.player import Player
from track_back.music_service.mock import MockMusicService


def _two_player_game() -> tuple[GameLogic, Player, Player]:
    game = GameLogic(target_song_count=3, music_service=MockMusicService())
    alice = Player("alice")
    bob = Player("bob")
    game.start_game(players=[alice, bob])
    return game, alice, bob


def test_round_does_not_advance_when_no_active_players_remain() -> None:
    game, alice, _bob = _two_player_game()

    assert game.player_disconnected("alice") is False
    assert game.player_disconnected("bob") is False

    game.player_rejoined("alice")
    game.handle_guess("alice", 0)
    assert [song.title for song in alice.song_list] == ["Yesterday"]


def test_round_advances_when_last_owed_player_leaves() -> None:
    game, alice, _bob = _two_player_game()

    game.handle_guess("alice", 0)
    assert game.player_disconnected("bob") is True

    game.handle_guess("alice", 1)
    assert [song.title for song in alice.song_list] == [
        "Yesterday",
        "Bohemian Rhapsody",
    ]
