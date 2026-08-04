# Health score rules

The [health score](../README.md#dataset-health-score)'s default weights and
severities work for a generic dataset, but "how bad is this, really" is
genuinely different across teams: a negative value in a `price` column might
be a hard blocker for a billing team and a shrug for someone doing rough
exploratory analysis. A YAML rules file lets you say that explicitly,
instead of everyone arguing over one fixed score.

Requires the `rules` extra:

```bash
pip install data-detective-toolkit[rules]
```

Passing `--rules` (or the API's `rules_file`) without it installed raises a
clear error telling you to install it, not a crash. It's optional and not a
hard dependency, in keeping with this project's lightweight positioning.

## The problem this solves

By default, every check either costs you points (a `warning`) or doesn't
(`info`, e.g. near-constant/date-like columns, tracked but not scored). None
of them can fail a build on their own; you're stuck reading the number. A
rules file adds a third severity, `failure`, and lets you say a specific
category, or even a specific column within a category, should actually stop
CI.

## Basic usage

```bash
data-detective analyze data.csv --rules team-rules.yaml
```

A rules file only needs to specify what it's overriding; everything else
keeps its default weight and severity.

## Schema

```yaml
categories:
  <category name>:
    weight: <number>      # optional, overrides the default cap for this category
    severity: <severity>  # optional: info | warning | failure

column_overrides:
  - column: <column name>
    category: <category name>
    severity: <severity>  # info | warning | failure
    weight: <number>      # optional
```

Valid category names are the same keys `health_score`'s `breakdown` already
returns: `missing_values`, `duplicate_rows`, `outliers`, `duplicate_columns`,
`constant_columns`, `mixed_type_columns`, `negative_values`,
`skewed_distributions`, `correlated_columns`, plus the two informational-by-
default categories, `near_constant_columns` and `date_like_columns`. An
unknown category name, an invalid severity, or category weights that would
sum past 100 all raise a clear error rather than being silently ignored.

## Worked example: the `price` column scenario

```yaml
column_overrides:
  - column: price
    category: negative_values
    severity: failure
```

```bash
data-detective analyze sales.csv --rules price-rules.yaml --fail-on failure
```

A negative value in any *other* non-negative-implying column (`quantity`,
`amount`, etc.) still costs points as a `warning`, same as always. A
negative value specifically in `price` does too, but now also lands in the
report's `health_score.failures` list, and `--fail-on failure` makes the CLI
exit non-zero because of it, printing which categories failed.

## Gating CI on failures

```bash
data-detective analyze incoming.csv --rules team-rules.yaml --fail-on failure --quiet
```

This is a better fit for a CI gate than counting outliers with `jq` (see
[Advanced usage](advanced-usage.md#gate-a-ci-pipeline-on-data-quality)):
it's specific to the categories your team actually cares about, and a
category with `severity: warning` (or the default, no rules file at all)
never fails the build, no matter how many points it costs.

## REST API

`POST /api/analyze` accepts an optional second file field, `rules_file`,
alongside `file`:

```bash
curl -F "file=@data.csv" -F "rules_file=@team-rules.yaml" "http://localhost:8000/api/analyze"
```

## Using it as a Python library

```python
from data_detective.profiler import DataProfiler
from data_detective.rules import load_rules

rules = load_rules("team-rules.yaml", base=DataProfiler.DEFAULT_RULES)
report = DataProfiler(df).run_full_profile(rules=rules)
```

`DataProfiler.DEFAULT_RULES` is what `health_score()` and `run_full_profile()`
already fall back to when no rules are given, so `load_rules(path, base=DataProfiler.DEFAULT_RULES)`
only needs to describe what's different for your team, not redeclare every
category.
