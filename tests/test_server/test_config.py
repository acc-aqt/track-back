from pathlib import Path

import platformdirs
import pytest
from platformdirs.windows import Windows

from track_back.server import config


def test_windows_user_config_is_directly_under_local_app_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_app_data = r"C:\Users\host\AppData\Local"
    monkeypatch.setattr(platformdirs, "PlatformDirs", Windows)
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", local_app_data)

    assert config.user_config_path() == Path(local_app_data) / "track-back" / ".env"
