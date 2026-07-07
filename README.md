# 🕵️ Data Detective

[![Tests](https://github.com/murs5l/data-detective/actions/workflows/tests.yml/badge.svg)](https://github.com/murs5l/data-detective/actions/workflows/tests.yml)

Point Data Detective at a CSV and get an automated data-quality intelligence
report back: shape, missing values, duplicates, outliers, high-cardinality
(likely ID) columns, correlated/duplicate columns, skew, and plain-English
insights — as a CLI, a JSON/HTML report, or a full web app you can run with
one command.

Two ways to use it:

- **CLI** — a local, pip-installable tool for scripting and CI pipelines.
- **Web app** — drag-and-drop a CSV in the browser, backed by a FastAPI
  service, with a live correlation heatmap and histograms.

Your data is never uploaded to a third party and never persisted to disk —
everything runs on infrastructure you control (your own machine, or your own
server via Docker).

---

## Web app (backend + frontend)

The fastest way to try Data Detective:

```bash
docker compose up --build
```

Then open **http://localhost:8000** and drop in a CSV.

Under the hood:

- `backend/` — a FastAPI service that wraps the same profiling engine as the
  CLI (`POST /api/analyze` for JSON, `POST /api/analyze/html` for a
  standalone HTML report). Uploads are validated (extension, size, empty
  file) and processed entirely in memory / a short-lived temp file — nothing
  is written to persistent storage.
- `frontend/` — a dependency-free HTML/CSS/JS single-page app: insights lead,
  technical tables (missing %, outliers, correlation pairs, etc.) are tucked
  behind a "Full technical report" toggle so the page reads clearly for
  non-technical users while still giving data engineers the full detail.
- `tools/fastscan/` — a small Go CLI that streams a CSV once to report
  row/column counts and delimiter in milliseconds. The backend calls it
  (if present) for an instant "quick scan" stat alongside the full pandas
  profile; if it's missing (e.g. a plain `pip install` without Go), the app
  works identically without it.

To run the backend directly without Docker:

```bash
pip install -e ".[api]"
uvicorn backend.app.main:app --reload
```

## CLI

```bash
git clone https://github.com/murs5l/data-detective.git
cd data-detective
pip install -e .
```

```bash
data-detective analyze path/to/file.csv
```

| Flag               | Description                                    |
|--------------------|-------------------------------------------------|
| `--json`           | Print the full report as JSON                    |
| `--html`           | Generate `report.html` in the CWD                |
| `--output-json`    | Write JSON report to a given file path            |
| `--output-html`    | Write HTML report to a given file path            |
| `--outlier-method` | `iqr` or `mad` (default) outlier detection        |
| `--quiet`          | Suppress non-error progress messages              |

```bash
data-detective analyze sample.csv --html
```

## What it detects

- Shape, column types, missing values (count + %)
- Duplicate rows and duplicate columns
- Constant (no-variation) columns
- High-cardinality columns (likely IDs)
- Outliers (IQR or MAD method) on numeric columns
- Highly correlated numeric column pairs + full correlation matrix
- Histogram bins per numeric column
- Columns that look like dates but aren't parsed as such
- Mixed-type columns and unexpected negative values (e.g. a negative `age`)
- Text column length stats (blank/whitespace-only values, min/max length)
- Skewed distributions and per-column memory footprint

## Development

```bash
# core engine + CLI
pip install -e ".[dev]"
pytest tests

# backend API
pip install -e ".[api]"
pip install -r backend/requirements-dev.txt
pytest backend/tests

# fastscan (Go speed layer)
cd tools/fastscan && go test ./...
```

CI runs all three (`.github/workflows/tests.yml`) on every push and PR.

## Roadmap

- GitHub Action to run Data Detective as a data-quality gate in CI
- Support for additional sources (Parquet, JSON, database connections)
- Scheduled/hosted profiling for pipelines beyond ad-hoc uploads

## License

See [LICENSE](LICENSE).
