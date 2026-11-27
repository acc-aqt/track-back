"""Full application/game tests for integration of Apple Music."""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from game.game_logic import GameLogic
from game.user import User
from music_service.apple_music import AppleMusicAdapter
from music_service.covers import COVER_URL_PREFIX, cover_store


@pytest.mark.skipif(
    not (
        AppleMusicAdapter.running_on_macos()
        and AppleMusicAdapter.music_app_is_running()
    ),
    reason="Needs macOS with Apple Music running",
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

    assert game.is_game_over() is True

    winner = game.winner

    assert winner == user_1  # First user instantly wins after first input
    assert len(winner.song_list) == 1


ORIGINAL_ARTWORK = b"original artwork bytes"
RESIZED_COVER = b"resized cover bytes"


class FakeMac:
    """Stands in for osascript and sips, as seen through subprocess.run."""

    def __init__(
        self,
        artwork: bytes | None,
        sips_works: bool = True,
        sips_missing: bool = False,
        export_hangs: bool = False,
    ) -> None:
        self.artwork = artwork
        self.sips_works = sips_works
        self.sips_missing = sips_missing
        self.export_hangs = export_hangs

    def run(
        self, args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args[0] == "sips":
            return self._sips(args)
        script = args[2]
        if "artwork" in script:
            return self._export_artwork(Path(args[3]))
        if "TrackBackSeparator" in script:
            return self._done(
                "YesterdayTrackBackSeparatorThe BeatlesTrackBackSeparator1965"
            )
        return self._done("true")

    def _export_artwork(self, path: Path) -> subprocess.CompletedProcess[str]:
        if self.export_hangs:
            raise subprocess.TimeoutExpired("osascript", timeout=5)
        if self.artwork is None:
            return self._done("none")
        path.write_bytes(self.artwork)
        return self._done("ok")

    def _sips(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if self.sips_missing:
            raise FileNotFoundError("sips")
        if not self.sips_works:
            return self._done("", returncode=1)
        Path(args[args.index("--out") + 1]).write_bytes(RESIZED_COVER)
        return self._done("")

    @staticmethod
    def _done(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


@pytest.fixture
def fake_mac(monkeypatch: pytest.MonkeyPatch) -> Callable[[FakeMac], AppleMusicAdapter]:
    always = staticmethod(lambda: True)
    monkeypatch.setattr(AppleMusicAdapter, "running_on_macos", always)
    monkeypatch.setattr(AppleMusicAdapter, "music_app_is_running", always)

    def adapter_on(mac: FakeMac) -> AppleMusicAdapter:
        monkeypatch.setattr(subprocess, "run", mac.run)
        return AppleMusicAdapter()

    return adapter_on


def _served_cover(url: str) -> bytes | None:
    assert url.startswith(COVER_URL_PREFIX)
    return cover_store.get(url.removeprefix(COVER_URL_PREFIX))


def test_current_song_has_resized_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK))

    song = adapter.current_song()

    assert song.title == "Yesterday"
    assert _served_cover(song.album_cover_url) == RESIZED_COVER


def test_current_song_without_artwork_has_no_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=None))

    assert adapter.current_song().album_cover_url == ""


def test_cover_falls_back_to_original_artwork_when_sips_fails(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, sips_works=False))

    song = adapter.current_song()

    assert _served_cover(song.album_cover_url) == ORIGINAL_ARTWORK


def test_cover_falls_back_to_original_artwork_when_sips_is_missing(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, sips_missing=True))

    song = adapter.current_song()

    assert _served_cover(song.album_cover_url) == ORIGINAL_ARTWORK


def test_hanging_artwork_export_leaves_song_without_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, export_hangs=True))

    song = adapter.current_song()

    assert song.title == "Yesterday"
    assert song.album_cover_url == ""
