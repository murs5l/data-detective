# 🕵️ Data Detective

A smart data profiling CLI tool for CSV files. Point it at a dataset and get
a quick intelligence report: shape, missing values, duplicates, outliers,
high-cardinality (likely ID) columns, correlated columns, and more —
in your terminal, as JSON, or as an HTML report.

## Install

```bash
git clone https://github.com/murs5l/data-detective.git
# 🕵️ Data Detective

A smart data profiling CLI tool for CSV files. Point it at a dataset and get
a quick intelligence report: shape, missing values, duplicates, outliers,
high-cardinality (likely ID) columns, correlated columns, and more —
in your terminal, as JSON, or as an HTML report.

## Install

```bash
git clone https://github.com/murs5l/data-detective.git
cd data-detective
pip install -e .
```

## Usage

```bash
data-detective analyze path/to/file.csv
```

Options:

| Flag      | Description                        |
|-----------|-------------------------------------|
| `--json`  | Print the full report as JSON       |
| `--html`  | Generate `report.html` in the CWD   |

Example:

```bash
data-detective analyze sample.csv --html
```

## What it detects

- Shape, column types, missing values (count + %)
- Duplicate rows and duplicate columns
- Constant (no-variation) columns
- High-cardinality columns (likely IDs)
- Outliers (IQR method) on numeric columns
- Highly correlated numeric column pairs
- Columns that look like dates but aren't parsed as such

## Development

```bash
pip install -e ".[dev]"   # or: pip install pytest
pytest
```

## License

See [LICENSE](LICENSE).

## Development

```bash
pip install -e ".[dev]"   # or: pip install pytest
pytest
```

## License

See [LICENSE](LICENSE).
