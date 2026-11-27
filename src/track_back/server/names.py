r"""Validation rules for user input: user names, game ids and the Target Song Count.

The name rule matches the browser's NAME_PATTERN in web_ui/script.js:
/^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u
"""

import unicodedata
from collections.abc import Callable
from typing import Annotated

from pydantic import AfterValidator, Field

USER_NAME_MAX_LENGTH = 20
GAME_ID_MAX_LENGTH = 40


def _is_name_character(character: str) -> bool:
    return unicodedata.category(character)[0] in "LN" or character in "_-"


def is_valid_name(name: str, max_length: int) -> bool:
    """Return True if name has only letters, digits, '_' and '-', words split by one space."""
    words = name.split(" ")
    return len(name) <= max_length and all(
        word and all(_is_name_character(character) for character in word)
        for word in words
    )


def _name_validator(max_length: int) -> Callable[[str], str]:
    def validate(name: str) -> str:
        if not is_valid_name(name, max_length):
            raise ValueError(
                f"must have up to {max_length} letters, digits, '_', '-' "
                "and single spaces between words"
            )
        return name

    return validate


UserName = Annotated[str, AfterValidator(_name_validator(USER_NAME_MAX_LENGTH))]
GameId = Annotated[str, AfterValidator(_name_validator(GAME_ID_MAX_LENGTH))]
TargetSongCount = Annotated[int, Field(ge=1)]
