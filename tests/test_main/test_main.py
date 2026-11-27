import importlib
import itertools
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


@pytest.fixture(autouse=True)
def user_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "user-config"
    monkeypatch.setattr(
        "track_back.server.config.user_config_path",
        lambda: config_dir / ".env",
    )
    monkeypatch.setenv("PORT", "unset-after-test")
    monkeypatch.delenv("PORT")
    return config_dir


def run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> mock.MagicMock:
    sys.argv = ["track-back-server", *argv]
    main_module = importlib.import_module("track_back.server.main")
    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)
    main_module.main()
    return mock_server


def test_main_uses_port_from_user_config_from_unrelated_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_config_dir: Path
) -> None:
    user_config_dir.mkdir()
    (user_config_dir / ".env").write_text("PORT=6001\n")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    server = run_main(monkeypatch, [])

    server.run.assert_called_once_with(port=6001)


def test_main_exits_when_env_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "missing.env"

    with pytest.raises(SystemExit) as excinfo:
        run_main(monkeypatch, ["--env-file", str(missing)])

    assert excinfo.value.code != 0
    assert f"env file not found: {missing}" in capsys.readouterr().err


SOURCES = ["environment", "env_file", "cwd_dotenv", "user_config"]


def configure_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ports: dict[str, int]
) -> list[str]:
    """Set PORT in each named source, chdir to a fresh directory, return argv."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    argv: list[str] = []
    for source, port in ports.items():
        if source == "environment":
            monkeypatch.setenv("PORT", str(port))
        elif source == "env_file":
            env_file = tmp_path / "chosen.env"
            env_file.write_text(f"PORT={port}\n")
            argv = ["--env-file", str(env_file)]
        elif source == "cwd_dotenv":
            (cwd / ".env").write_text(f"PORT={port}\n")
        else:
            user_file = tmp_path / "user-config" / ".env"
            user_file.parent.mkdir()
            user_file.write_text(f"PORT={port}\n")
    return argv


@pytest.mark.parametrize(("higher", "lower"), list(itertools.combinations(SOURCES, 2)))
def test_higher_precedence_config_source_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, higher: str, lower: str
) -> None:
    argv = configure_port(monkeypatch, tmp_path, {lower: 7002, higher: 7001})

    server = run_main(monkeypatch, argv)

    server.run.assert_called_once_with(port=7001)


@pytest.mark.parametrize("source", SOURCES)
def test_port_option_overrides_port_from_every_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str
) -> None:
    argv = configure_port(monkeypatch, tmp_path, {source: 7001})

    server = run_main(monkeypatch, [*argv, "--port", "8123"])

    server.run.assert_called_once_with(port=8123)


def test_version_flag_prints_package_version_and_exits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    expected_version = tomllib.loads(pyproject.read_text())["project"]["version"]

    with pytest.raises(SystemExit) as exit_info:
        run_main(monkeypatch, ["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"track-back-server {expected_version}"
