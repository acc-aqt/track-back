"""Domain errors raised by the game logic."""


class MusicPlaybackError(Exception):
    """The music service could not start playback."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            "Failed to play music. Please check if music service "
            f"{service_name} is running!"
        )
