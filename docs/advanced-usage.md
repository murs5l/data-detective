# Advanced usage

## Post a data-quality summary as a PR comment

Using the `gh` CLI in a GitHub Actions workflow:

```bash
data-detective analyze incoming.csv --output-markdown summary.md --quiet
gh pr comment "$PR_NUMBER" --body-file summary.md
```

The health score and insights lead the comment; the rest of the technical
detail is tucked into a collapsed `<details>` block GitHub renders natively.

## Gate a CI pipeline on data quality

Fail the build if outlier count exceeds a threshold:

```bash
data-detective analyze incoming.csv --json | jq '.outliers_mad | length' | xargs -I {} bash -c 'exit {}'
```

## Batch processing

Profile every CSV in a directory:

```bash
for f in data/*.csv; do
  data-detective analyze "$f" --output-html "reports/$(basename $f .csv).html"
done
```

## Choosing an outlier detection method

- **`mad`** (default): Median Absolute Deviation. Robust to skewed data and
  extreme values, since it's based on the median rather than the mean.
  Recommended for most real-world data.
- **`iqr`**: classic box-and-whisker (Q1/Q3-based). More familiar, but more
  sensitive to already-skewed distributions, since Q1/Q3 themselves shift
  with skew.

Both methods run on every analysis; the report includes both `outliers_mad`
and `outliers_iqr`, and `--outlier-method` only controls which one feeds the
health score and generated insights.

## Using Data Detective as a Python library

The CLI, web app, and REST API are all thin wrappers around one class. You
can call it directly in your own scripts or notebooks:

```python
import pandas as pd
from data_detective.profiler import DataProfiler

df = pd.read_csv("myfile.csv")
report = DataProfiler(df).run_full_profile(outlier_method="mad")

print(report["health_score"])
print(report["insights"])
```

`run_full_profile()` returns the exact same dict structure documented in the
[API reference](api-reference.md): the CLI's `--json` output, the API's
`/api/analyze` response body, and this dict are identical.

## Running the web app without Docker

```bash
pip install -e ".[api]"
uvicorn backend.app.main:app --reload
```

Then visit `http://localhost:8000`. The frontend (`frontend/`) is served
directly by the backend as static files, no build step required.

## Development setup, testing, and releasing

See [CONTRIBUTING.md](../CONTRIBUTING.md).
