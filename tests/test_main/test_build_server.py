import pytest
from pathlib import Path
from game.strategies.sequential import SequentialStrategy
from game.strategies.simultaneous import SimultaneousStrategy
from server.main import build_server
from music_service.apple_music import AppleMusicAdapter
from music_service.spotify import SpotifyAdapter

@pytest.mark.skipif(not AppleMusicAdapter.running_on_macos(), reason="Test only runs on macOS")
@pytest.mark.skipif(
    not AppleMusicAdapter.music_app_is_running(),
    reason="Apple Music is not running",
)
def test_build_server_apple_simultaneous():
    config_path = Path(__file__).parent / "test_apple_simultaneous.toml"

    server = build_server(config_path=config_path, target_song_count=3)

    assert server.game.target_song_count == 3
    assert isinstance(server.game.strategy, SimultaneousStrategy)
    assert isinstance(server.game.music_service, AppleMusicAdapter)
    assert server.connection_manager is not None

def test_build_server_spotify_sequential():
    config_path = Path(__file__).parent / "test_spotify_sequential.toml"

    server = build_server(config_path=config_path, target_song_count=3)

    assert server.game.target_song_count == 3
    assert isinstance(server.game.strategy, SequentialStrategy)
    assert isinstance(server.game.music_service, SpotifyAdapter)
    assert server.connection_manager is not None