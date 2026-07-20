# What it detects

Data Detective automatically flags 20+ data quality issues:

**Structure & Completeness**
- Shape (rows × columns) and column data types
- Missing values (count and percentage per column)
- Duplicate rows
- Duplicate columns (identical data, different names)
- Constant columns (no variation; e.g., all 1s)
- Near-constant columns (one value dominates 95%+ of rows; easy to miss since they "look" like they vary)
- Possible modeling target column (name-based, e.g. `target`, `label`, `churn`, `y`)

**Statistical Issues**
- Outliers: IQR method (classic box-and-whisker) or MAD (robust for skewed data)
- Highly correlated numeric pairs
- Skewed distributions (heavy left/right tails)
- Kurtosis (fat tails or sharp peaks)

**Data Type & Value Issues**
- High-cardinality columns (likely IDs or keys)
- Mixed-type columns (e.g., numbers and strings in the same column)
- Unexpected negative values (e.g., negative `age`, `price`, `quantity`)
- Date-like values not parsed as datetime

**Text Columns**
- Length statistics (min, max, average)
- Blank or whitespace-only values

**Aggregates**
- Full numeric correlation matrix
- Histograms with bin edges and counts for numeric columns
- Five-number summary (min, Q1, median, Q3, max) per numeric column
- Per-column memory footprint (KB)

**Output**
- A 0-100 data health score with a documented, inspectable breakdown (not a black box); see [the Health Score section](../README.md#dataset-health-score) in the README
- Plain-English actionable insights highlighting the most important issues
- JSON, HTML, or Markdown export (the Markdown format is built for pasting into a PR comment or CI summary)

Every detector above lives in `DataProfiler` (`src/data_detective/profiler.py`)
and is exercised by the CLI, the web app, and the REST API identically; see
[Architecture](../README.md#architecture) in the README.
