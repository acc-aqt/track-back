"""Keeps album cover images that the server hands out to browsers."""

import hashlib

COVER_URL_PREFIX = "/covers/"


class CoverStore:
    """In-memory album cover images, keyed by a hash of their bytes."""

    def __init__(self) -> None:
        self._covers: dict[str, bytes] = {}

    def add(self, image: bytes) -> str:
        """Store the image and return its id."""
        cover_id = hashlib.sha256(image).hexdigest()
        self._covers[cover_id] = image
        return cover_id

    def get(self, cover_id: str) -> bytes | None:
        """Return the image with this id, or None if it is unknown."""
        return self._covers.get(cover_id)


def cover_url(cover_id: str) -> str:
    """Return the server-relative URL a browser loads the cover from."""
    return f"{COVER_URL_PREFIX}{cover_id}"
