## Releasing

Releases are published by `.github/workflows/release.yml` when a `v*` tag is pushed.

1. Set `version` in `pyproject.toml` (e.g. `0.2.0`) and merge it to `main`.
2. Tag that commit and push the tag:

   ```sh
   git tag v0.2.0
   git push origin v0.2.0
   ```

The workflow fails before building if the tag is not `v` plus the `pyproject.toml`
version (check locally with `python scripts/check_release_tag.py v0.2.0`). It then
builds the sdist and wheel once, smoke-tests the wheel, and publishes those same
files to TestPyPI and, only if that succeeds, to PyPI.

### One-time setup

Publishing uses PyPI Trusted Publishing; the repository holds no API tokens.

1. On GitHub, under *Settings → Environments*, create the environments `testpypi`
   and `pypi`. Optionally add required reviewers to `pypi` to approve each release.
2. On [pypi.org](https://pypi.org/manage/account/publishing/) and
   [test.pypi.org](https://test.pypi.org/manage/account/publishing/) (separate
   accounts), add a *pending publisher* (the project does not exist yet):

   | Field             | pypi.org      | test.pypi.org |
   | ----------------- | ------------- | ------------- |
   | PyPI project name | `track-back`  | `track-back`  |
   | Owner             | `acc-aqt`     | `acc-aqt`     |
   | Repository name   | `track-back`  | `track-back`  |
   | Workflow name     | `release.yml` | `release.yml` |
   | Environment name  | `pypi`        | `testpypi`    |

   The first successful release turns the pending publisher into a normal one.
