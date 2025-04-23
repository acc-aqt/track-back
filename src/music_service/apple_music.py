"""Implementation of the AppleMusicClient class."""

# pylint: disable=line-too-long

import subprocess
import sys

from game.song import Song
from music_service.abstract_adapter import AbstractMusicServiceAdapter

OSA_SCRIPT_PATH = "osascript"


class AppleMusicAdapter(AbstractMusicServiceAdapter):
    """Uses AppleScripts to interact with Apple Music."""

    def __init__(self) -> None:
        if not self.running_on_macos():
            raise RuntimeError("Apple Music is only supported on macOS!")
        if not self.music_app_is_running():
            raise RuntimeError("Apple Music is not running!")
    
    def authenticate(self) -> None:
        """Authenticate the user with the music service."""
        # No authentication needed for Apple Music
        pass

    def current_song(self) -> Song:
        """Get the currently playing song."""
        if not self._music_is_playing():
            self.start_playback()

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
            raise RuntimeError(
                f"Failed to parse the current song information. "
                f"Output was '{result.stdout}'. Check if a song is playing!"
            ) from err

        release_year_int = int(release_year) if release_year.isdigit() else 0

        return Song(title=track_name, artist=artist_name, release_year=release_year_int)

    def start_playback(self) -> None:
        """Start playing music."""
        script = """
    tell application "Music"
        play
    end tell
    """

        subprocess.run([OSA_SCRIPT_PATH, "-e", script], check=False)  # noqa: S603

    def _music_is_playing(self) -> bool:
        script = """
    tell application "Music"
        return player state is playing
    end tell
    """
        result = subprocess.run(  # noqa: S603
            [OSA_SCRIPT_PATH, "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip().lower() == "true"

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
