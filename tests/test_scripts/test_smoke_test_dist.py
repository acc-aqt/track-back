from pathlib import Path

import pytest
from smoke_test_dist import find_distributions, missing_web_ui_files


def make_dist(root: Path, *files: str) -> Path:
    for name in files:
        (root / name).write_text("x")
    return root


def test_finds_the_wheel_and_sdist(tmp_path: Path) -> None:
    dist = make_dist(
        tmp_path, "track_back-0.1.0-py3-none-any.whl", "track_back-0.1.0.tar.gz"
    )
    assert find_distributions(dist) == (
        dist / "track_back-0.1.0-py3-none-any.whl",
        dist / "track_back-0.1.0.tar.gz",
    )


@pytest.mark.parametrize(
    "files",
    [
        ("track_back-0.1.0.tar.gz",),
        ("track_back-0.1.0-py3-none-any.whl",),
        (
            "track_back-0.1.0-py3-none-any.whl",
            "track_back-0.2.0-py3-none-any.whl",
            "track_back-0.1.0.tar.gz",
        ),
    ],
)
def test_rejects_dist_without_exactly_one_wheel_and_sdist(
    tmp_path: Path, files: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError):
        find_distributions(make_dist(tmp_path, *files))


def make_web_ui(root: Path, *files: str) -> Path:
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return root


def test_no_files_missing_when_installed_matches_source(tmp_path: Path) -> None:
    source = make_web_ui(tmp_path, "index.html", "dummy-cover/cover1.webp")
    installed = {"index.html", "dummy-cover/cover1.webp"}
    assert missing_web_ui_files(source, installed) == []


def test_reports_source_files_absent_from_installed_package(tmp_path: Path) -> None:
    source = make_web_ui(tmp_path, "index.html", "script.js", "dummy-cover/cover1.webp")
    assert missing_web_ui_files(source, {"index.html"}) == [
        "dummy-cover/cover1.webp",
        "script.js",
    ]
