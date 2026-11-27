"""Check that a release tag matches the version in pyproject.toml.

Usage: ``python scripts/check_release_tag.py v0.1.0``
"""

import argparse
import sys
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def tag_error(tag: str, pyproject: Path) -> str | None:
    """Return why a release tag does not match the project version, if it does not.

    Parameters
    ----------
    tag
        The release tag, e.g. ``v0.1.0``.
    pyproject
        Path to the project's ``pyproject.toml``.

    Returns
    -------
    str | None
        An error message, or ``None`` if the tag is ``v`` plus the version.
    """
    with pyproject.open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    expected = f"v{version}"
    if tag != expected:
        return f"tag {tag} does not match version {version} in {pyproject} ({expected})"
    return None


def main(argv: list[str] | None = None) -> int:
    """Check the tag given on the command line.

    Parameters
    ----------
    argv
        Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit code: 0 if the tag matches, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="release tag, e.g. v0.1.0")
    parser.add_argument(
        "--pyproject", type=Path, default=PYPROJECT, help="path to pyproject.toml"
    )
    args = parser.parse_args(argv)
    error = tag_error(args.tag, args.pyproject)
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"tag {args.tag} matches the project version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
