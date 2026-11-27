import io
import tarfile
from pathlib import Path

import pytest
from smoke_test_dist import (
    find_distributions,
    missing_web_ui_files,
    reported_version,
    sdist_web_ui_files,
)


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


def make_sdist(path: Path, *members: str) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        for name in members:
            info = tarfile.TarInfo(name)
            tar.addfile(info, io.BytesIO())
    return path


def test_lists_web_ui_files_inside_the_sdist(tmp_path: Path) -> None:
    sdist = make_sdist(
        tmp_path / "track_back-0.1.0.tar.gz",
        "track_back-0.1.0/pyproject.toml",
        "track_back-0.1.0/src/track_back/__init__.py",
        "track_back-0.1.0/src/track_back/web_ui/index.html",
        "track_back-0.1.0/src/track_back/web_ui/dummy-cover/cover1.webp",
    )
    assert sorted(sdist_web_ui_files(sdist)) == [
        "dummy-cover/cover1.webp",
        "index.html",
    ]


def test_reads_version_from_version_output() -> None:
    assert reported_version("track-back-server 1.2.3\n") == "1.2.3"
