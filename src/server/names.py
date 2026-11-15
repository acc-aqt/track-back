"""Validation rules for user names and game ids shown in the web UI."""

import re

NAME_PATTERN = r"^[\w-]+( [\w-]+)*$"
USER_NAME_MAX_LENGTH = 20
GAME_ID_MAX_LENGTH = 40


def is_valid_name(name: str, max_length: int) -> bool:
    """Return True if name uses only letters, digits, '_', '-' and single spaces."""
    return len(name) <= max_length and re.fullmatch(NAME_PATTERN, name) is not None
