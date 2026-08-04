"""Configurable health-score rules: per-category weights and severities,
with optional per-column overrides.

Ships as an optional `rules` extra (PyYAML), not a hard dependency, matching
the project's zero-runtime-dependency-beyond-pandas/numpy positioning:
importing this module never requires PyYAML, only `load_rules()` actually
reading a file does, and it imports PyYAML lazily for that reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import DataDetectiveError

VALID_SEVERITIES = ("info", "warning", "failure")


class RulesError(DataDetectiveError):
    """Raised when a rules file is missing, malformed, or invalid."""


def _validate_severity(severity: str) -> None:
    if severity not in VALID_SEVERITIES:
        raise RulesError(f"Invalid severity {severity!r}; must be one of {VALID_SEVERITIES}.")


@dataclass
class CategoryRule:
    """The resolved weight/severity for one health-score category."""

    weight: float
    severity: str = "warning"

    def __post_init__(self) -> None:
        _validate_severity(self.severity)


@dataclass
class ColumnOverride:
    """A per-column override for one category, e.g. 'negative_values is a
    failure specifically on the price column, a warning everywhere else.'"""

    column: str
    category: str
    severity: str | None = None
    weight: float | None = None

    def __post_init__(self) -> None:
        if self.severity is not None:
            _validate_severity(self.severity)


@dataclass
class HealthScoreRules:
    """A fully resolved rules contract: every category's weight/severity,
    plus any column-specific overrides. `DataProfiler.DEFAULT_RULES` is one
    of these, built from `HEALTH_SCORE_MAX_DEDUCTIONS`; `load_rules()`
    returns another, merged from a YAML file onto a base."""

    categories: dict[str, CategoryRule]
    column_overrides: list[ColumnOverride] = field(default_factory=list)

    def override_for(self, category: str, column: str) -> ColumnOverride | None:
        for override in self.column_overrides:
            if override.category == category and override.column == column:
                return override
        return None


def load_rules(path: str | Path, base: HealthScoreRules) -> HealthScoreRules:
    """Loads a YAML rules file and merges it onto `base` (typically
    `DataProfiler.DEFAULT_RULES`): a rules file only needs to specify what
    it's overriding, not the entire contract.

    Raises RulesError for: PyYAML not installed, an unreadable or
    malformed file, an unknown category name, an invalid severity, or
    category weights that would sum past 100.
    """
    try:
        import yaml
    except ImportError as e:
        raise RulesError(
            "Loading a rules file requires PyYAML. Install it with: "
            "pip install data-detective-toolkit[rules]"
        ) from e

    rules_path = Path(path)
    try:
        text = rules_path.read_text(encoding="utf-8")
    except OSError as e:
        raise RulesError(f"Could not read rules file {rules_path}: {e}") from e

    try:
        raw: Any = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise RulesError(f"Invalid YAML in rules file {rules_path}: {e}") from e

    if not isinstance(raw, dict):
        raise RulesError(f"Rules file {rules_path} must contain a YAML mapping at the top level.")

    categories_raw = raw.get("categories", {})
    if not isinstance(categories_raw, dict):
        raise RulesError("'categories' must be a mapping of category name to settings.")

    overrides_raw = raw.get("column_overrides", [])
    if not isinstance(overrides_raw, list):
        raise RulesError("'column_overrides' must be a list.")

    categories = dict(base.categories)
    for name, settings in categories_raw.items():
        if name not in categories:
            raise RulesError(f"Unknown category {name!r}. Valid categories: {sorted(categories)}.")
        if not isinstance(settings, dict):
            raise RulesError(f"Category {name!r} must map to a mapping of settings (weight/severity).")
        current = categories[name]
        categories[name] = CategoryRule(
            weight=settings.get("weight", current.weight),
            severity=settings.get("severity", current.severity),
        )

    total_weight = sum(c.weight for c in categories.values())
    if total_weight > 100:
        raise RulesError(f"Category weights sum to {total_weight}, which exceeds 100.")

    column_overrides = list(base.column_overrides)
    for i, item in enumerate(overrides_raw):
        if not isinstance(item, dict) or "column" not in item or "category" not in item:
            raise RulesError(f"column_overrides[{i}] must have both 'column' and 'category'.")
        category = item["category"]
        if category not in categories:
            raise RulesError(
                f"Unknown category {category!r} in column_overrides[{i}]. Valid categories: {sorted(categories)}."
            )
        column_overrides.append(
            ColumnOverride(
                column=item["column"],
                category=category,
                severity=item.get("severity"),
                weight=item.get("weight"),
            )
        )

    return HealthScoreRules(categories=categories, column_overrides=column_overrides)
