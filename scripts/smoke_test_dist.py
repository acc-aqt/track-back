"""Smoke-test built distributions of track-back.

Installs the wheel from a dist directory into a fresh virtual environment,
outside the source tree, and checks the installed tool and its Web UI files.

Usage: ``python scripts/smoke_test_dist.py dist``
"""

import argparse
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

SOURCE_WEB_UI = Path(__file__).resolve().parents[1] / "src" / "track_back" / "web_ui"

LIST_INSTALLED_WEB_UI = """
from pathlib import Path
import track_back

web_ui = Path(track_back.__file__).parent / "web_ui"
for path in web_ui.rglob("*"):
    if path.is_file():
        print(path.relative_to(web_ui).as_posix())
"""


def find_distributions(dist_dir: Path) -> tuple[Path, Path]:
    """Return the single wheel and single sdist in a dist directory.

    Parameters
    ----------
    dist_dir
        Directory holding the built distributions.

    Returns
    -------
    tuple[Path, Path]
        The wheel and the sdist.

    Raises
    ------
    ValueError
        If the directory does not hold exactly one wheel and one sdist.
    """
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        found = [path.name for path in wheels + sdists]
        msg = f"expected one wheel and one sdist in {dist_dir}, found {found}"
        raise ValueError(msg)
    return wheels[0], sdists[0]


def missing_web_ui_files(source_web_ui: Path, installed: Iterable[str]) -> list[str]:
    """Return Web UI files in the source tree that the installed package lacks.

    Parameters
    ----------
    source_web_ui
        The ``web_ui`` directory of the source tree.
    installed
        Paths of the installed Web UI files, relative to its ``web_ui`` directory.

    Returns
    -------
    list[str]
        Sorted relative POSIX paths of the missing files.
    """
    expected = {
        path.relative_to(source_web_ui).as_posix()
        for path in source_web_ui.rglob("*")
        if path.is_file()
    }
    return sorted(expected - set(installed))


def _run(*command: str | Path, cwd: Path) -> str:
    print("+", *command, flush=True)
    result = subprocess.run(  # noqa: S603
        [str(part) for part in command],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="", flush=True)
    return result.stdout


def smoke_test(wheel: Path) -> list[str]:
    """Install the wheel into a fresh venv and check the installed tool.

    Parameters
    ----------
    wheel
        The wheel to install.

    Returns
    -------
    list[str]
        Web UI files missing from the installed package.
    """
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        venv = workdir / "venv"
        bin_dir = venv / ("Scripts" if sys.platform == "win32" else "bin")
        _run(sys.executable, "-m", "venv", venv, cwd=workdir)
        _run(
            bin_dir / "python",
            "-m",
            "pip",
            "install",
            "-q",
            wheel.resolve(),
            cwd=workdir,
        )
        _run(bin_dir / "track-back-server", "--help", cwd=workdir)
        _run(bin_dir / "track-back-server", "--version", cwd=workdir)
        listing = _run(
            bin_dir / "python", "-I", "-c", LIST_INSTALLED_WEB_UI, cwd=workdir
        )
    return missing_web_ui_files(SOURCE_WEB_UI, listing.splitlines())


def main() -> int:
    """Run the smoke test against the dist directory given on the command line.

    Returns
    -------
    int
        Process exit code: 0 on success, 1 on any failure.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist_dir", type=Path, help="directory with wheel and sdist")
    args = parser.parse_args()
    try:
        wheel, _sdist = find_distributions(args.dist_dir)
        missing = smoke_test(wheel)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(error.stdout, error.stderr, sep="\n", file=sys.stderr)
        print(f"error: command failed: {error.cmd}", file=sys.stderr)
        return 1
    if missing:
        print("error: Web UI files missing from the wheel:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
