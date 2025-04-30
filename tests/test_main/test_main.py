import sys
import logging
from server.main import parse_args
import pytest
from unittest import mock
import importlib


@pytest.mark.parametrize(
    "argv, expected_port, expected_log_level",
    [
        (["main.py", "--port", "5000", "--log-level", "DEBUG"], 5000, logging.DEBUG),
        (["main.py", "--log-level", "WARNING"], 4200, logging.WARNING),
        (["main.py"], 4200, logging.INFO),
    ],
)
def test_parse_args(argv, expected_port, expected_log_level):
    # Arrange
    sys.argv = argv

    port, log_level = parse_args()

    # Assert
    assert port == expected_port
    assert log_level == expected_log_level


def test_main_runs_server(monkeypatch):
    # Arrange
    sys.argv = ["server/main.py", "--port", "4321", "--log-level", "DEBUG"]

    # Dynamically import the main module
    main_module = importlib.import_module("server.main")

    # Patch the Server class in server.main
    mock_server = mock.MagicMock()
    monkeypatch.setattr(main_module, "Server", lambda: mock_server)

    # Act
    main_module.main()

    # Assert
    mock_server.run.assert_called_once_with(port=4321)
