import importlib
import io
import itertools
import logging
import os
import sys
import tomllib
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def user_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "user-config"
    monkeypatch.setattr(
        "track_back.server.config.user_config_path",
        lambda: config_dir / ".env",
    )
    monkeypatch.delenv("PORT", raising=False)
    return config_dir


def run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> mock.MagicMock:
    monkeypatch.setattr(sys, "argv", ["track-back-server", *argv])
    main_module = importlib.import_module("track_back.server.main")
    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)
    main_module.main()
    return mock_server


@pytest.mark.parametrize(
    ("argv", "expected_port", "expected_log_level"),
    [
        (["--port", "5000", "--log-level", "DEBUG"], 5000, logging.DEBUG),
        (["--log-level", "WARNING"], 4200, logging.WARNING),
        ([], 4200, logging.INFO),
    ],
)
def test_main_starts_server_with_port_and_log_level_from_arguments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
    expected_port: int,
    expected_log_level: int,
) -> None:
    monkeypatch.chdir(tmp_path)
    basic_config = mock.MagicMock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)

    server = run_main(monkeypatch, argv)

    server.run.assert_called_once_with(port=expected_port)
    basic_config.assert_called_once_with(level=expected_log_level)


def test_main_uses_port_from_dotenv_in_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("PORT=5555\n")
    monkeypatch.chdir(tmp_path)

    server = run_main(monkeypatch, [])

    server.run.assert_called_once_with(port=5555)


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

    assert excinfo.value.code == 2
    assert f"env file not found: {missing}" in capsys.readouterr().err


SOURCES = ["environment", "env_file", "cwd_dotenv", "user_config"]


def configure_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    user_config_dir: Path,
    ports: dict[str, int],
) -> list[str]:
    """Set PORT in each named source, chdir to a fresh directory, return argv."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    argv: list[str] = []

    def set_environment(port: int) -> None:
        monkeypatch.setenv("PORT", str(port))

    def set_env_file(port: int) -> None:
        env_file = tmp_path / "chosen.env"
        env_file.write_text(f"PORT={port}\n")
        argv.extend(["--env-file", str(env_file)])

    def set_cwd_dotenv(port: int) -> None:
        (cwd / ".env").write_text(f"PORT={port}\n")

    def set_user_config(port: int) -> None:
        user_config_dir.mkdir()
        (user_config_dir / ".env").write_text(f"PORT={port}\n")

    setters = {
        "environment": set_environment,
        "env_file": set_env_file,
        "cwd_dotenv": set_cwd_dotenv,
        "user_config": set_user_config,
    }
    for source, port in ports.items():
        setters[source](port)
    return argv


@pytest.mark.parametrize(("higher", "lower"), list(itertools.combinations(SOURCES, 2)))
def test_higher_precedence_config_source_wins(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    user_config_dir: Path,
    higher: str,
    lower: str,
) -> None:
    argv = configure_port(
        monkeypatch, tmp_path, user_config_dir, {lower: 7002, higher: 7001}
    )

    server = run_main(monkeypatch, argv)

    server.run.assert_called_once_with(port=7001)


@pytest.mark.parametrize("source", SOURCES)
def test_port_option_overrides_port_from_every_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_config_dir: Path, source: str
) -> None:
    argv = configure_port(monkeypatch, tmp_path, user_config_dir, {source: 7001})

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


def run_init(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> mock.MagicMock:
    monkeypatch.setattr(sys, "stdin", io.StringIO("".join(f"{a}\n" for a in answers)))
    return run_main(monkeypatch, ["init"])


def test_init_writes_user_config_from_answers(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    server = run_init(
        monkeypatch,
        ["5000", "y", "my-id", "my-secret", "https://example.com/callback"],
    )

    assert (user_config_dir / ".env").read_text() == (
        "PORT=5000\n"
        "SSL_KEYFILE=\n"
        "SSL_CERTFILE=\n"
        "SPOTIPY_CLIENT_ID=my-id\n"
        "SPOTIPY_CLIENT_SECRET=my-secret\n"
        "SPOTIPY_REDIRECT_URI=https://example.com/callback\n"
    )
    server.run.assert_not_called()


def test_init_enter_accepts_default_port(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    run_init(monkeypatch, ["", "n"])

    assert "PORT=4200\n" in (user_config_dir / ".env").read_text()


def test_init_default_redirect_uri_uses_chosen_port(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    run_init(monkeypatch, ["5000", "y", "my-id", "my-secret", ""])

    assert "SPOTIPY_REDIRECT_URI=http://127.0.0.1:5000/spotify-callback\n" in (
        (user_config_dir / ".env").read_text()
    )


def test_init_skipping_spotify_writes_empty_keys_without_prompting(
    monkeypatch: pytest.MonkeyPatch,
    user_config_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_init(monkeypatch, ["", "n"])

    written = (user_config_dir / ".env").read_text()
    assert "SPOTIPY_CLIENT_ID=\n" in written
    assert "SPOTIPY_CLIENT_SECRET=\n" in written
    assert "SPOTIPY_REDIRECT_URI=\n" in written
    assert "client ID" not in capsys.readouterr().out


def test_init_creates_missing_config_directory_and_prints_path(
    monkeypatch: pytest.MonkeyPatch,
    user_config_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not user_config_dir.exists()

    run_init(monkeypatch, ["", "n"])

    assert (user_config_dir / ".env").is_file()
    assert str(user_config_dir / ".env") in capsys.readouterr().out


EXISTING_CONFIG = b"PORT=6001\r\n# hand-edited\n"


def test_init_overwrites_existing_config_when_confirmed(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    user_config_dir.mkdir()
    (user_config_dir / ".env").write_bytes(EXISTING_CONFIG)

    run_init(monkeypatch, ["y", "5000", "n"])

    assert "PORT=5000\n" in (user_config_dir / ".env").read_text()


def test_init_leaves_existing_config_unchanged_when_declined(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    user_config_dir.mkdir()
    (user_config_dir / ".env").write_bytes(EXISTING_CONFIG)

    run_init(monkeypatch, ["n", "5000", "n"])

    assert (user_config_dir / ".env").read_bytes() == EXISTING_CONFIG


SPOTIFY_KEYS = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]


def test_server_started_from_unrelated_directory_uses_values_from_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for key in SPOTIFY_KEYS:
        monkeypatch.delenv(key, raising=False)
    run_init(monkeypatch, ["5000", "y", "my-id", "my-secret", ""])
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    server = run_main(monkeypatch, [])

    server.run.assert_called_once_with(port=5000)
    assert os.environ["SPOTIPY_CLIENT_ID"] == "my-id"


def test_help_lists_init_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        run_main(monkeypatch, ["-h"])

    assert "init" in capsys.readouterr().out


def test_init_asks_again_when_port_is_not_a_number(
    monkeypatch: pytest.MonkeyPatch, user_config_dir: Path
) -> None:
    run_init(monkeypatch, ["abc", "5000", "n"])

    assert "PORT=5000\n" in (user_config_dir / ".env").read_text()
