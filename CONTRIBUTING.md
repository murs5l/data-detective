# Contributing to Data Detective

Thanks for considering a contribution! This project has three moving parts —
a Python profiling engine + CLI, a FastAPI backend, and a dependency-free
frontend — plus an optional Go speed layer. This guide covers how to get set
up and what to expect when opening a PR.

## Getting set up

```bash
git clone https://github.com/murs5l/data-detective.git
cd data-detective

# core engine + CLI
pip install -e ".[dev]"
pytest tests

# backend API (optional, only if touching backend/)
pip install -e ".[api]"
pip install -r backend/requirements-dev.txt
pytest backend/tests

# fastscan, the Go speed layer (optional, only if touching tools/fastscan)
cd tools/fastscan && go test ./...
```

To run the full web app locally while developing:

```bash
uvicorn backend.app.main:app --reload
```

Then open `http://localhost:8000`. The frontend (`frontend/`) is served
directly by the backend as static files, no build step required.

## Before opening a PR

1. **Add tests** for new behavior. `tests/` covers the profiling engine,
   `backend/tests/` covers the API. A bug fix should include a regression
   test; a new detector or endpoint should include coverage for its main
   path and at least one edge case (empty data, all-null column, etc.).
2. **Run the full suite** and make sure it's green:
   ```bash
   pytest tests backend/tests
   ```
3. **Keep changes focused.** Prefer several small, reviewable PRs over one
   large one covering unrelated changes.
4. **Match the existing style.** No em dashes in prose, no unnecessary
   comments (only comment the *why*, not the *what*), and prefer editing
   existing files over adding new abstractions.

## Reporting bugs

Open an issue using the Bug Report template. Include:

- A minimal CSV (or description of the data shape) that reproduces the issue
- What you expected vs. what happened
- Whether you're using the CLI, the web app, or the API directly

## Proposing features

Open an issue using the Feature Request template first, especially for
anything that changes the CLI's flags, the report schema, or the API's
public contract. That way we can agree on the shape of the change before
you invest time in an implementation.

## Releasing

1. Add an entry to [CHANGELOG.md](CHANGELOG.md) under a new `## [x.y.z] - YYYY-MM-DD`
   heading (Added/Fixed/Changed, following [Keep a Changelog](https://keepachangelog.com/)).
   The release workflow extracts this section automatically for the GitHub
   Release body, an untagged version gets a placeholder instead, so this
   step isn't optional.
2. Bump `version` in `pyproject.toml` to match.
3. Commit, push, then tag and push the tag:
   ```bash
   git tag vx.y.z
   git push origin vx.y.z
   ```
4. This triggers `.github/workflows/release.yml`: builds the package,
   publishes to PyPI (if `PUBLISH_TO_PYPI` is set), pushes a Docker image to
   GHCR, and creates the GitHub Release.

Use a minor bump (`0.x.0`) for new user-facing functionality, a patch
(`0.0.x`) for fixes only.

## Security issues

Please do **not** open a public issue for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for how to report them privately.

## Code of Conduct

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you're expected to uphold it.
