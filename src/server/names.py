"""Validation rules for user input: user names, game ids and the Target Song Count."""

import re
from typing import Annotated

from pydantic import Field

NAME_PATTERN = r"^[\w-]+( [\w-]+)*$"
USER_NAME_MAX_LENGTH = 20
GAME_ID_MAX_LENGTH = 40

TargetSongCount = Annotated[int, Field(ge=1)]


def is_valid_name(name: str, max_length: int) -> bool:
    """Return True if name uses only letters, digits, '_', '-' and single spaces."""
    return len(name) <= max_length and re.fullmatch(NAME_PATTERN, name) is not None
