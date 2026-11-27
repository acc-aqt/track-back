"""Full application/game tests for integration of Apple Music."""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from track_back.game.game_logic import GameLogic
from track_back.game.player import Player
from track_back.music_service.apple_music import AppleMusicAdapter
from track_back.music_service.covers import COVER_URL_PREFIX, CoverStore
from track_back.music_service.error import MusicServiceError


@pytest.mark.skipif(
    not (
        AppleMusicAdapter.running_on_macos()
        and AppleMusicAdapter.music_app_is_running()
    ),
    reason="Needs macOS with Apple Music running",
)
def test_full_game_one_round() -> None:
    """Test a full game with one round."""
    player_1 = Player("Elton")
    player_2 = Player("John")

    music_service = AppleMusicAdapter(CoverStore())
    game = GameLogic(
        target_song_count=1,
        music_service=music_service,
    )
    game.start_game(players=[player_1, player_2])
    # Simulate one user input: "0" to insert at start

    game.handle_guess("Elton", 0)

    assert game.is_game_over() is True

    winner = game.winner

    assert winner == player_1  # First player instantly wins after first input
    assert len(winner.timeline) == 1


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
        playing: bool = True,
    ) -> None:
        self.artwork = artwork
        self.playing = playing
        self.scripts: list[str] = []
        self.sips_works = sips_works
        self.sips_missing = sips_missing
        self.export_hangs = export_hangs

    def run(
        self, args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args[0] == "sips":
            return self._sips(args)
        script = args[2]
        self.scripts.append(script)
        if "artwork" in script:
            return self._export_artwork(Path(args[3]))
        if "TrackBackSeparator" in script:
            if not self.playing:
                return self._done("No song is currently playing")
            return self._done(
                "YesterdayTrackBackSeparatorThe BeatlesTrackBackSeparator1965"
            )
        if "player state is playing" in script:
            return self._done(str(self.playing).lower())
        return self._done("true")

    def started_playback(self) -> bool:
        return any(
            line.strip() == "play"
            for script in self.scripts
            for line in script.split("\n")
        )

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
def covers() -> CoverStore:
    return CoverStore()


@pytest.fixture
def fake_mac(
    monkeypatch: pytest.MonkeyPatch, covers: CoverStore
) -> Callable[[FakeMac], AppleMusicAdapter]:
    always = staticmethod(lambda: True)
    monkeypatch.setattr(AppleMusicAdapter, "running_on_macos", always)
    monkeypatch.setattr(AppleMusicAdapter, "music_app_is_running", always)

    def adapter_on(mac: FakeMac) -> AppleMusicAdapter:
        monkeypatch.setattr(subprocess, "run", mac.run)
        return AppleMusicAdapter(covers)

    return adapter_on


def _served_cover(covers: CoverStore, url: str) -> bytes | None:
    assert url.startswith(COVER_URL_PREFIX)
    return covers.get(url.removeprefix(COVER_URL_PREFIX))


def test_current_song_has_resized_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
    covers: CoverStore,
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK))

    song = adapter.current_song()

    assert song.title == "Yesterday"
    assert _served_cover(covers, song.album_cover_url) == RESIZED_COVER


def test_current_song_without_artwork_has_no_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=None))

    assert adapter.current_song().album_cover_url == ""


def test_cover_falls_back_to_original_artwork_when_sips_fails(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
    covers: CoverStore,
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, sips_works=False))

    song = adapter.current_song()

    assert _served_cover(covers, song.album_cover_url) == ORIGINAL_ARTWORK


def test_cover_falls_back_to_original_artwork_when_sips_is_missing(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
    covers: CoverStore,
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, sips_missing=True))

    song = adapter.current_song()

    assert _served_cover(covers, song.album_cover_url) == ORIGINAL_ARTWORK


def test_hanging_artwork_export_leaves_song_without_cover(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    adapter = fake_mac(FakeMac(artwork=ORIGINAL_ARTWORK, export_hangs=True))

    song = adapter.current_song()

    assert song.title == "Yesterday"
    assert song.album_cover_url == ""


def test_current_song_while_paused_raises_without_starting_playback(
    fake_mac: Callable[[FakeMac], AppleMusicAdapter],
) -> None:
    mac = FakeMac(artwork=None, playing=False)
    adapter = fake_mac(mac)

    with pytest.raises(MusicServiceError):
        adapter.current_song()

    assert not mac.started_playback()
