"""Tests that the API reports the installed package version."""

import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def test_openapi_document_reports_package_version(client: TestClient) -> None:
    expected_version = tomllib.loads(PYPROJECT.read_text())["project"]["version"]

    response = client.get("/openapi.json")

    assert response.json()["info"]["version"] == expected_version
