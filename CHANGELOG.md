# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Markdown report export (`--markdown` / `--output-markdown` CLI flags, `POST /api/analyze/markdown`, and a "Download Markdown" button in the web app): health score and insights lead, technical detail collapses into a `<details>` block for pasting into a PR comment or CI summary.
- A progress bar during analysis in the web app, replacing the bare spinner. Eases toward 90% while the request is in flight and completes to 100% on response, since the backend doesn't stream real progress events.

## [0.4.0] - 2026-07-17

### Added
- Data health score: a 0-100 score computed from existing detector outputs, with a documented, inspectable breakdown (not a black box). Surfaced in the CLI's text report, the web app, and the static HTML report.
- Near-constant column detection: flags columns where one value covers 95%+ of rows but the column isn't fully constant.
- Possible modeling-target column detection: conservative, name-based (`target`, `label`, `churn`, a bare `y`, etc.).
- `--version` flag on the CLI, reads the installed package version dynamically.
- Type hints across the core engine (`profiler.py`) and CLI, checked in CI via `mypy`.
- Test coverage tracking in CI, with an auto-updating badge in the README (currently 94%+).
- `docs/` folder with a demo GIF and screenshots embedded in the README.
- Architecture section in the README: project structure and how the CLI/web app/REST API share one profiling engine.

### Fixed
- The static HTML report used to bury Insights as the last of 16 sections, with every technical table always expanded. It now leads with Insights and collapses technical detail, matching the web app.
- A CI config bug (`mypy`'s `python_version` pin) that broke the type-check job outright.
- Coverage badge generation, which depended on a third-party tool broken by a recent `setuptools` release; replaced with a small self-written script.

### Changed
- `pandas`/`numpy` version bounds tightened (`pandas<4.0`, `numpy<3.0`) so a future major bump is a deliberate decision, not a silent `pip install` surprise.

## [0.3.1] - 2026-07-15

### Changed
- Renamed the PyPI package to `data-detective-toolkit` (the name `data-detective` was too similar to an existing package and was rejected by PyPI's similarity check). The installed command remains `data-detective`.

## [0.3.0] - 2026-07-12

Initial public release: CLI, FastAPI backend, web app, optional Go speed layer, and the core profiling engine (missing values, duplicates, outliers, correlations, distribution shape, ID-like column detection, and more).
