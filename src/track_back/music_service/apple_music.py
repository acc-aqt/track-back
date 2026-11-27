"""Implementation of the AppleMusicAdapter class."""

import subprocess
import sys
import tempfile
from pathlib import Path

from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.covers import CoverStore, cover_url
from track_back.music_service.error import MusicServiceError

OSA_SCRIPT_PATH = "osascript"
SIPS_PATH = "sips"
COVER_SIZE_PX = 300
COVER_TIMEOUT_SECONDS = 5

EXPORT_ARTWORK_SCRIPT = """
on run argv
    tell application "Music"
        if (count of artworks of current track) is 0 then return "none"
        set artworkData to raw data of artwork 1 of current track
    end tell
    set outFile to open for access (POSIX file (item 1 of argv)) with write permission
    try
        set eof outFile to 0
        write artworkData to outFile
    on error errorMessage
        close access outFile
        error errorMessage
    end try
    close access outFile
    return "ok"
end run
"""


class AppleMusicAdapter(AbstractMusicServiceAdapter):
    """Uses AppleScripts to interact with Apple Music.

    Parameters
    ----------
    cover_store : CoverStore
        Where the album covers of the current Songs are published.
    """

    service_name = "Apple Music"

    def __init__(self, cover_store: CoverStore) -> None:
        if not self.running_on_macos():
            raise MusicServiceError("Apple Music is only supported on macOS!")
        if not self.music_app_is_running():
            raise MusicServiceError("Apple Music is not running!")
        self._cover_store = cover_store

    def current_song(self) -> Song:
        """Get the currently playing song."""
        separator = "TrackBackSeparator"
        script = f"""
    tell application "Music"
        if player state is playing then
            set trackName to name of current track
            set artistName to artist of current track
            set releaseYear to year of current track
            return trackName & "{separator}" & artistName & "{separator}" & releaseYear
        else
            return "No song is currently playing"
        end if
    end tell
    """
        result = subprocess.run(  # noqa: S603
            [OSA_SCRIPT_PATH, "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            track_name, artist_name, release_year = result.stdout.strip().split(
                separator
            )
        except ValueError as err:
            raise MusicServiceError(
                f"Failed to parse the current song information. "
                f"Output was '{result.stdout}'. Check if a song is playing!"
            ) from err

        release_year_int = int(release_year) if release_year.isdigit() else 0

        return Song(
            title=track_name,
            artist=artist_name,
            release_year=release_year_int,
            album_cover_url=self._current_cover_url(),
        )

    def _current_cover_url(self) -> str:
        """Return the URL of the current track's cover, or "" if it has none."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            artwork_path = Path(tmp_dir) / "artwork"
            try:
                result = subprocess.run(  # noqa: S603
                    [OSA_SCRIPT_PATH, "-e", EXPORT_ARTWORK_SCRIPT, str(artwork_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=COVER_TIMEOUT_SECONDS,
                )
            except (OSError, subprocess.SubprocessError):
                return ""
            if result.stdout.strip() != "ok" or not artwork_path.is_file():
                return ""
            image = _resized_to_jpeg(artwork_path) or artwork_path.read_bytes()
        return cover_url(self._cover_store.add(image))

    def start_playback(self) -> None:
        """Start playing music."""
        script = """
    tell application "Music"
        play
    end tell
    """

        subprocess.run([OSA_SCRIPT_PATH, "-e", script], check=False)  # noqa: S603

    def next_track(self) -> None:
        """Skip to the next track."""
        script = """
    tell application "Music"
        next track
    end tell
    """
        subprocess.run([OSA_SCRIPT_PATH, "-e", script], check=False)  # noqa: S603

    @staticmethod
    def running_on_macos() -> bool:
        """Return True if the OS is macOS."""
        return sys.platform == "darwin"

    @staticmethod
    def music_app_is_running() -> bool:
        """Return True if the Music app is running."""
        script = (
            'tell application "System Events" to (name of processes) contains "Music"'
        )
        result = subprocess.run(  # noqa: S603
            [OSA_SCRIPT_PATH, "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip().lower() == "true"


def _resized_to_jpeg(image_path: Path) -> bytes | None:
    """Return the image shrunk to a small JPEG, or None if sips fails."""
    out_path = image_path.with_suffix(".jpg")
    try:
        result = subprocess.run(  # noqa: S603
            [
                SIPS_PATH,
                "-s",
                "format",
                "jpeg",
                "-Z",
                str(COVER_SIZE_PX),
                str(image_path),
                "--out",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=COVER_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not out_path.is_file():
        return None
    return out_path.read_bytes()
