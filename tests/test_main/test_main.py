import importlib
import logging
import sys
import tomllib
from pathlib import Path
from unittest import mock

import pytest

from track_back.server.main import parse_args


@pytest.mark.parametrize(
    ("argv", "expected_port", "expected_log_level"),
    [
        (["main.py", "--port", "5000", "--log-level", "DEBUG"], 5000, logging.DEBUG),
        (["main.py", "--log-level", "WARNING"], 4200, logging.WARNING),
        (["main.py"], 4200, logging.INFO),
    ],
)
def test_parse_args(
    argv: list[str], expected_port: int, expected_log_level: int
) -> None:
    sys.argv = argv

    port, log_level = parse_args()

    assert port == expected_port
    assert log_level == expected_log_level


def test_main_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.argv = ["server/main.py", "--port", "4321", "--log-level", "DEBUG"]

    main_module = importlib.import_module("track_back.server.main")

    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)

    main_module.main()

    mock_server.run.assert_called_once_with(port=4321)


def test_main_uses_port_from_dotenv_in_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sys.argv = ["server/main.py"]
    monkeypatch.setenv("PORT", "unset-after-test")
    monkeypatch.delenv("PORT")
    (tmp_path / ".env").write_text("PORT=5555\n")
    monkeypatch.chdir(tmp_path)

    main_module = importlib.import_module("track_back.server.main")

    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)

    main_module.main()

    mock_server.run.assert_called_once_with(port=5555)


def test_version_flag_prints_package_version_and_exits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    expected_version = tomllib.loads(pyproject.read_text())["project"]["version"]
    sys.argv = ["track-back-server", "--version"]

    main_module = importlib.import_module("track_back.server.main")

    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)

    with pytest.raises(SystemExit) as exit_info:
        main_module.main()

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"track-back-server {expected_version}"
    mock_server.run.assert_not_called()
