"""Implementation of the AppleMusicClient class."""

import sys
import subprocess
from music_providers.abstract_music_provider import AbstractMusicProvider

from game.song import Song


class AppleMusicClient(AbstractMusicProvider):
    """Uses AppleScripts to interact with Apple Music."""

    def __init__(self):
        if not self._running_on_macos():
            raise RuntimeError("Apple Music is only supported on macOS!")
        if not self._music_app_is_running():
            raise RuntimeError("Apple Music is not running!")

    def current_song(self) -> Song:
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
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        try:
            track_name, artist_name, release_year = result.stdout.strip().split(separator)
        except ValueError:
            raise RuntimeError("Failed to parse the current song information. Check if a song is playing!")

        return Song(title=track_name, artist=artist_name, release_year=release_year)

    def start_playback(self) -> None:
        script = """
    tell application "Music"
        play
    end tell
    """

        subprocess.run(["osascript", "-e", script])

    def _music_is_playing(self) -> bool:
        script = """
    tell application "Music"
        return player state is playinƒg
    end tell
    """
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return result.stdout.strip().lower() == "true"

    def next_track(self) -> None:
        script = """
    tell application "Music"
        next track
    end tell
    """
        subprocess.run(["osascript", "-e", script])

    def _running_on_macos(self):
        return sys.platform == "darwin"

    def _music_app_is_running(self):
        script = 'tell application "System Events" to (name of processes) contains "Music"'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return result.stdout.strip().lower() == "true"
