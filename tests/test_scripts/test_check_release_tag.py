from pathlib import Path

import pytest
from check_release_tag import main, tag_error


def write_pyproject(tmp_path: Path, version: str) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f'[project]\nname = "track-back"\nversion = "{version}"\n')
    return pyproject


def test_accepts_tag_matching_the_project_version(tmp_path: Path) -> None:
    assert tag_error("v1.2.3", write_pyproject(tmp_path, "1.2.3")) is None


@pytest.mark.parametrize("tag", ["v1.2.4", "1.2.3", "v1.2.3rc1", "vv1.2.3"])
def test_rejects_tag_not_matching_the_project_version(tmp_path: Path, tag: str) -> None:
    error = tag_error(tag, write_pyproject(tmp_path, "1.2.3"))
    assert error is not None
    assert tag in error
    assert "v1.2.3" in error


def test_cli_fails_on_mismatching_tag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = write_pyproject(tmp_path, "1.2.3")
    assert main(["v1.2.4", "--pyproject", str(pyproject)]) == 1
    assert "v1.2.4" in capsys.readouterr().err


def test_cli_succeeds_on_matching_tag(tmp_path: Path) -> None:
    pyproject = write_pyproject(tmp_path, "1.2.3")
    assert main(["v1.2.3", "--pyproject", str(pyproject)]) == 0
