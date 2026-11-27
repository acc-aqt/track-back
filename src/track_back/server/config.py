"""Locate and load the server configuration from dotenv files."""

from pathlib import Path

import platformdirs
from dotenv import find_dotenv, load_dotenv

APP_NAME = "track-back"


def user_config_path() -> Path:
    """Return the path of the per-user config file.

    Returns
    -------
    Path
        The ``.env`` file in the platform's user config directory for TrackBack.
    """
    return Path(platformdirs.user_config_dir(APP_NAME)) / ".env"


def load_config(env_file: Path | None = None) -> None:
    """Load config into the environment without overriding variables already set.

    Sources, highest precedence first: real environment variables, ``env_file``,
    ``.env`` in the current working directory, the per-user config file.

    Parameters
    ----------
    env_file : Path | None
        An explicitly chosen dotenv file, if any.
    """
    if env_file is not None:
        load_dotenv(env_file)
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(user_config_path())
