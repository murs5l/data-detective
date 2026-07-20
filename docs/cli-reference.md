# CLI reference

## Installation

```bash
pip install data-detective-toolkit
```

> **macOS tip:** if `data-detective` comes back as `command not found` right after
> installing, pip likely fell back to a `--user` install (common on macOS's system
> Python, since its site-packages isn't writeable) and the resulting `bin/` folder
> isn't on your `PATH`. Two fixes:
>
> - **Recommended:** install with [pipx](https://pipx.pypa.io) instead, which
>   installs CLI tools in an isolated environment and wires up `PATH` for you.
>   Run each line separately, then restart your terminal before the last step:
>   ```bash
>   brew install pipx
>   pipx ensurepath
>   ```
>   ```bash
>   pipx install data-detective-toolkit
>   ```
>   (No Homebrew? Use `python3 -m pip install --user pipx` instead of the first line.)
> - **Or** find where pip actually put it and add that to your `PATH`:
>   ```bash
>   python3 -m site --user-base
>   ```
>   This prints something like `/Users/you/Library/Python/3.9`. Add `<that path>/bin`
>   to `PATH` in `~/.zshrc`, then restart your terminal.

## Basic usage

```bash
# Print a text summary to stdout
data-detective analyze myfile.csv

# Generate an interactive HTML report
data-detective analyze myfile.csv --html

# Generate a Markdown report (for PR/CI comments)
data-detective analyze myfile.csv --markdown

# Output JSON for programmatic use
data-detective analyze myfile.csv --json | jq '.insights'

# Write to specific files
data-detective analyze myfile.csv --output-html reports/q1_data.html
```

## Options

| Flag                | Description                                         | Example                                    |
|---------------------|------------------------------------------------------|---------------------------------------------|
| `--json`            | Print full report as JSON to stdout                  | `data-detective analyze data.csv --json`    |
| `--html`            | Generate `report.html` in current directory           | `data-detective analyze data.csv --html`    |
| `--markdown`        | Generate `report.md` in current directory             | `data-detective analyze data.csv --markdown`|
| `--output-json`     | Write JSON report to a specific file path             | `--output-json reports/profile.json`        |
| `--output-html`     | Write HTML report to a specific file path             | `--output-html reports/profile.html`        |
| `--output-markdown` | Write Markdown report to a specific file path         | `--output-markdown reports/profile.md`      |
| `--outlier-method`  | Choose outlier detection: `iqr` or `mad` (default)    | `--outlier-method iqr`                      |
| `--quiet`           | Suppress non-error progress messages                  | `--quiet`                                   |
| `--version`         | Print the installed version and exit                  | `data-detective --version`                  |

## Examples

**Basic report on stdout:**
```bash
data-detective analyze myfile.csv
```

**Data validation:** check for specific issues before ETL
```bash
data-detective analyze input.csv --quiet --json | jq '.high_cardinality_columns'
```

See [advanced usage](advanced-usage.md) for CI/CD gating, batch processing, and
posting a Markdown report straight to a GitHub PR.
