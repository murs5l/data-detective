from __future__ import annotations

import hashlib
import re
from functools import cached_property
from typing import Any

import numpy as np
import pandas as pd

from .rules import CategoryRule, HealthScoreRules


class DataProfiler:
    """
    Advanced Data Detective engine.
    Adds statistical intelligence + anomaly detection.
    """

    HIGH_CARDINALITY_THRESHOLD = 0.9
    CORRELATION_THRESHOLD = 0.9
    # Above this many numeric columns, a full n x n correlation matrix
    # (2,500+ cells) stops being something anyone can usefully read or
    # render as a heatmap, even though computing it is still fast. Show
    # the top correlated pairs instead of the full matrix, with a notice
    # explaining why, rather than silently dumping an unusable payload.
    MAX_COLUMNS_FOR_FULL_CORRELATION = 50
    TOP_CORRELATED_PAIRS_LIMIT = 50
    # 0.75 quantile of the standard normal distribution; scales MAD so it's
    # comparable to standard deviation for normally distributed data.
    MAD_Z_CONSTANT = 0.6745
    IQR_MULTIPLIER = 1.5
    # Iglewicz & Hoaglin's conventional cutoff for the modified z-score.
    MAD_OUTLIER_THRESHOLD = 3.5
    DATETIME_SUCCESS_RATIO = 0.8
    SKEWNESS_THRESHOLD = 2.0
    NONNEGATIVE_KEYWORDS = ("count", "age", "price", "quantity", "amount", "qty", "total")
    ID_NAME_WORDS = frozenset({
        "id", "uuid", "guid", "key", "code", "number", "num", "no", "index", "idx", "ref",
    })
    # Share of non-null rows the single most common value must reach to
    # flag a column as "near-constant" (distinct from detect_constant_columns,
    # which only catches columns with exactly one unique value).
    NEAR_CONSTANT_THRESHOLD = 0.95
    # "y" is deliberately excluded here and handled separately as a full-name
    # match only: as a word within a compound name (e.g. "y_coordinate",
    # "pos_y") it's just as likely to mean a spatial axis as an ML target.
    TARGET_NAME_WORDS = frozenset({
        "target", "label", "labels", "class", "outcome", "churn",
        "response", "result", "diagnosis", "prediction", "output",
    })

    # Health score: starts at 100, each category deducts up to its cap,
    # scaled by how bad that category actually is (not just present/absent).
    # Caps sum to 100 so a dataset hitting every cap simultaneously floors
    # at 0; in practice most datasets only trip a few categories.
    HEALTH_SCORE_MAX_DEDUCTIONS = {
        "missing_values": 25,
        "duplicate_rows": 20,
        "outliers": 15,
        "duplicate_columns": 10,
        "constant_columns": 10,
        "mixed_type_columns": 5,
        "negative_values": 5,
        "skewed_distributions": 5,
        "correlated_columns": 5,
        # Tracked but not scored by default: whether a near-constant or
        # date-like column is actually a problem depends on context a
        # generic score can't know (e.g. a near-constant "country" column
        # might be entirely expected). Zero weight, not omission, so the
        # distinction between "checked and found unremarkable" and "not
        # checked at all" is explicit rather than silent. See
        # `informational_categories` in health_score()'s return value.
        "near_constant_columns": 0,
        "date_like_columns": 0,
    }
    HEALTH_SCORE_GRADES = (
        (90, "Excellent"),
        (75, "Good"),
        (60, "Fair"),
        (40, "Poor"),
        (0, "Critical"),
    )

    # The rules health_score() falls back to when no `rules` argument is
    # given: every category at its HEALTH_SCORE_MAX_DEDUCTIONS weight,
    # "warning" severity except the two zero-weight informational
    # categories. This *is* the default, not an approximation of it, so
    # calling health_score() and health_score(rules=DataProfiler.DEFAULT_RULES)
    # always produce identical output. Load a YAML file with `load_rules()`
    # (src/data_detective/rules.py) to override weights/severities per team.
    DEFAULT_RULES = HealthScoreRules(
        categories={
            name: CategoryRule(weight=cap, severity="info" if cap == 0 else "warning")
            for name, cap in HEALTH_SCORE_MAX_DEDUCTIONS.items()
        }
    )

    # Tuning constants for health_score()'s per-category deductions. Named
    # so there's one place to find and adjust them, rather than magic
    # numbers buried in the method body. Each was set empirically against
    # sample messy data, not derived from a formal model; the comment next
    # to each deduction in health_score() explains the reasoning behind
    # its specific value.
    MISSING_VALUES_WORST_COLUMN_WEIGHT = 0.7
    MISSING_VALUES_AVERAGE_WEIGHT = 0.3
    OUTLIER_CELL_RATIO_SCALE = 100
    DUPLICATE_COLUMN_POINTS_PER_OCCURRENCE = 3
    CONSTANT_COLUMN_POINTS_PER_OCCURRENCE = 3
    MIXED_TYPE_POINTS_PER_OCCURRENCE = 2.5
    NEGATIVE_VALUES_POINTS_PER_OCCURRENCE = 2.5
    SKEWED_RATIO_SCALE = 2
    CORRELATED_PAIR_POINTS = 1
    # Only meaningful if a caller raises these categories' cap above 0 via
    # a rules override; unused at the default weight of 0.
    NEAR_CONSTANT_COLUMN_POINTS_PER_OCCURRENCE = 3
    DATE_LIKE_COLUMN_POINTS_PER_OCCURRENCE = 2

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    # -------------------------
    # CACHED INTERNAL STATE (computed once, reused everywhere)
    # -------------------------

    @cached_property
    def _numeric_df(self) -> pd.DataFrame:
        return self.df.select_dtypes(include=[np.number])

    @cached_property
    def _nunique(self) -> pd.Series:
        return self.df.nunique()

    @cached_property
    def _null_counts(self) -> pd.Series:
        return self.df.isnull().sum()

    @cached_property
    def _quantiles(self) -> pd.DataFrame:
        """Q1/Q3 for all numeric columns computed once."""
        if self._numeric_df.empty:
            return pd.DataFrame()
        return self._numeric_df.quantile([0.25, 0.75])

    @cached_property
    def _correlation_matrix_raw(self) -> pd.DataFrame:
        """Unrounded pandas .corr() output, computed once. Both
        detect_correlated_columns() and correlation_matrix() need this;
        .corr() is O(columns^2 * rows), too expensive to redo twice per
        profile just because two different callers want different
        post-processing (abs()+threshold vs. round()+fillna())."""
        if self._numeric_df.shape[1] < 2:
            return pd.DataFrame()
        return self._numeric_df.corr()

    # -------------------------
    # BASIC STRUCTURE
    # -------------------------

    def shape(self) -> dict[str, int]:
        return {"rows": self.df.shape[0], "columns": self.df.shape[1]}

    def column_types(self) -> dict[str, str]:
        return self.df.dtypes.astype(str).to_dict()

    def missing_values(self) -> dict[str, int]:
        return self._null_counts.to_dict()

    def missing_percentage(self) -> dict[str, float]:
        if len(self.df) == 0:
            return {}
        return (self._null_counts / len(self.df) * 100).round(2).to_dict()

    def duplicate_rows(self) -> int:
        return int(self.df.duplicated().sum())

    def unique_counts(self) -> dict[str, int]:
        return self._nunique.to_dict()

    # -------------------------
    # INTELLIGENCE LAYER
    # -------------------------

    def detect_constant_columns(self) -> list[str]:
        return self._nunique[self._nunique <= 1].index.tolist()

    def detect_near_constant_columns(self) -> list[str]:
        """
        Flags columns where one value dominates almost all non-null rows
        (default 95%+) but the column isn't fully constant. These are easy
        to miss since they "look" like they vary, but carry almost no
        information, arguably a subtler problem than a true constant
        column, which at least is obvious at a glance.
        """
        flagged: list[str] = []
        for col in self.df.columns:
            series = self.df[col].dropna()
            if series.empty or series.nunique() <= 1:
                continue  # empty or fully constant; detect_constant_columns handles that
            top_share = series.value_counts(normalize=True).iloc[0]
            if top_share >= self.NEAR_CONSTANT_THRESHOLD:
                flagged.append(col)
        return flagged

    def detect_possible_target_columns(self) -> list[str]:
        """
        Best-effort guess at which column(s) could be a modeling target.
        Name-based only (e.g. 'target', 'label', 'churn'), matched as whole
        words, deliberately conservative: guessing from cardinality or
        position alone (e.g. "the last binary column") produces far too
        many false positives on ordinary feature columns to be useful.
        """
        matches = []
        for col in self.df.columns:
            if col.strip().lower() == "y" or any(w in self.TARGET_NAME_WORDS for w in self._name_words(col)):
                matches.append(col)
        return matches

    @staticmethod
    def _name_words(col: str) -> list[str]:
        """Splits a column name into lowercase whole words (handles snake_case,
        kebab-case, and camelCase), so name-based detectors can match on whole
        words rather than substrings (e.g. so 'TotalPay' doesn't match 'total')."""
        spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", col)
        return [w.lower() for w in re.split(r"[^a-zA-Z0-9]+", spaced) if w]

    def _name_looks_like_identifier(self, col: str) -> bool:
        """True if the column name itself suggests an ID/key (e.g. 'employee_id')."""
        return any(w in self.ID_NAME_WORDS for w in self._name_words(col))

    def _is_sequential_integer_column(self, col: str) -> bool:
        """True if a numeric column is a gapless run of integers (e.g. 1..N), the
        classic shape of an auto-increment key or row index."""
        series = self.df[col].dropna()
        if series.empty or (series % 1 != 0).any():
            return False
        value_range = series.max() - series.min() + 1
        return series.nunique() == len(series) == value_range

    def detect_high_cardinality(self, threshold: float | None = None, min_unique: int = 10) -> list[str]:
        """
        Flags columns that are likely identifiers rather than measurements.
        High uniqueness alone isn't enough: a continuous numeric column (e.g.
        salary, price) is often just as unique per-row as a real ID, so we
        only flag it when the name itself looks ID-like (e.g. 'employee_id')
        or, for numeric columns, when the values form a gapless integer run
        (e.g. 1..N), the signature of an auto-increment key or row index.
        Non-numeric columns (strings/objects) keep the uniqueness-only check,
        since near-unique text (emails, UUIDs) is a strong identifier signal
        on its own.
        """
        if threshold is None:
            threshold = self.HIGH_CARDINALITY_THRESHOLD
        if len(self.df) == 0:
            return []

        ratio = self._nunique / len(self.df)
        mask = (ratio >= threshold) & (self._nunique >= min_unique)
        candidates = self._nunique[mask].index.tolist()

        return [
            col for col in candidates
            if self._name_looks_like_identifier(col)
            or col not in self._numeric_df.columns
            or self._is_sequential_integer_column(col)
        ]

    def _calculate_iqr_bounds(self, series: pd.Series) -> tuple[float, float, float, float]:
        """Returns (q1, q3, lower_fence, upper_fence) for a numeric series."""
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower_fence = q1 - self.IQR_MULTIPLIER * iqr
        upper_fence = q3 + self.IQR_MULTIPLIER * iqr
        return q1, q3, lower_fence, upper_fence

    def detect_outliers(self, method: str = "iqr") -> dict[str, int]:
        """
        method: "iqr" (default) or "mad" (robust z-score, better for skewed data)
        Returns count per column.
        """
        outliers: dict[str, int] = {}

        if self._numeric_df.empty:
            return outliers

        for col in self._numeric_df.columns:
            series = self._numeric_df[col].dropna()
            if series.empty:
                outliers[col] = 0
                continue

            if method == "mad":
                median = series.median()
                mad = (series - median).abs().median()
                if mad == 0:
                    outliers[col] = 0
                    continue
                modified_z = self.MAD_Z_CONSTANT * (series - median) / mad
                count = (modified_z.abs() > self.MAD_OUTLIER_THRESHOLD).sum()
            else:
                _, _, lower, upper = self._calculate_iqr_bounds(series)
                count = ((series < lower) | (series > upper)).sum()

            outliers[col] = int(count)

        return outliers

    def distribution_shape(self) -> dict[str, dict[str, float]]:
        """
        Skewness and kurtosis for numeric columns, flagging columns where
        the mean/IQR-based stats alone would be misleading.
        """
        shape: dict[str, dict[str, float]] = {}
        for col in self._numeric_df.columns:
            series = self._numeric_df[col].dropna()
            if len(series) < 3:
                continue
            shape[col] = {
                "skewness": round(float(series.skew()), 3),
                "kurtosis": round(float(series.kurt()), 3),
            }
        return shape

    def detect_duplicate_columns(self) -> list[tuple[str, str]]:
        """
        Finds pairs of columns that are exactly identical.
        Returns a list of (col_a, col_b) tuples.

        Hash-buckets columns first (one O(columns * rows) pass) so the
        expensive pairwise .equals() check only ever runs within a bucket
        of columns that already hash identically, not across every
        possible pair. Duplicate columns are rare in practice, so most
        buckets end up with exactly one column and need no comparison at
        all; two different columns can never land in different buckets
        and be wrongly skipped (hash_pandas_object is a deterministic
        function of a column's values, so equal columns always hash
        equal), and .equals() still verifies every candidate pair before
        it's reported, so a hash collision between genuinely different
        columns can't produce a false positive either.
        """
        duplicates: list[tuple[str, str]] = []
        buckets: dict[bytes, list[str]] = {}

        for col in self.df.columns:
            digest = hashlib.sha256(pd.util.hash_pandas_object(self.df[col], index=False).values.tobytes()).digest()
            buckets.setdefault(digest, []).append(col)

        for cols_in_bucket in buckets.values():
            for i in range(len(cols_in_bucket)):
                for j in range(i + 1, len(cols_in_bucket)):
                    col_a, col_b = cols_in_bucket[i], cols_in_bucket[j]
                    if self.df[col_a].equals(self.df[col_b]):
                        duplicates.append((col_a, col_b))

        return duplicates

    def _is_wide_for_correlation(self) -> bool:
        return self._numeric_df.shape[1] > self.MAX_COLUMNS_FOR_FULL_CORRELATION

    def detect_correlated_columns(self, threshold: float | None = None) -> list[tuple[str, str, float]]:
        """
        Finds pairs of numeric columns with correlation above threshold.

        Above MAX_COLUMNS_FOR_FULL_CORRELATION numeric columns, truncated
        to the TOP_CORRELATED_PAIRS_LIMIT strongest pairs (by absolute
        correlation, strongest first) rather than every qualifying pair:
        see partial_analysis_notices().
        """
        if threshold is None:
            threshold = self.CORRELATION_THRESHOLD
        if self._numeric_df.shape[1] < 2:
            return []

        corr_matrix = self._correlation_matrix_raw.abs()
        pairs: list[tuple[str, str, float]] = []
        cols = corr_matrix.columns

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                value = corr_matrix.iloc[i, j]
                if pd.notna(value) and value >= threshold:
                    pairs.append((cols[i], cols[j], round(float(value), 3)))

        if self._is_wide_for_correlation():
            pairs.sort(key=lambda pair: pair[2], reverse=True)
            pairs = pairs[: self.TOP_CORRELATED_PAIRS_LIMIT]

        return pairs

    def correlation_matrix(self) -> dict[str, dict[str, float]]:
        """
        Full pairwise correlation matrix for numeric columns, as a
        nested dict: {col_a: {col_b: correlation_value, ...}, ...}.
        Used for heatmap visualization.

        Omitted (returns {}) above MAX_COLUMNS_FOR_FULL_CORRELATION
        numeric columns: an n x n matrix that large stops being
        renderable as a heatmap or a useful JSON payload, even though
        computing it is still fast. detect_correlated_columns() still
        surfaces the strongest pairs; see partial_analysis_notices().
        """
        if self._numeric_df.shape[1] < 2:
            return {}
        if self._is_wide_for_correlation():
            return {}

        corr = self._correlation_matrix_raw.round(3)
        # Replace NaN (e.g. constant columns) with 0 so it's JSON-safe.
        corr = corr.fillna(0)
        return {col: corr[col].to_dict() for col in corr.columns}

    def partial_analysis_notices(self) -> list[str]:
        """Human-readable notices when part of the report was
        deliberately abbreviated for a very wide dataset, rather than
        silently truncated with no explanation."""
        notices: list[str] = []
        if self._is_wide_for_correlation():
            numeric_cols = self._numeric_df.shape[1]
            notices.append(
                f"Correlation matrix omitted: {numeric_cols} numeric columns exceeds the "
                f"{self.MAX_COLUMNS_FOR_FULL_CORRELATION}-column display limit. Showing the "
                f"top {self.TOP_CORRELATED_PAIRS_LIMIT} correlated pairs instead."
            )
        return notices

    def histogram_data(self, bins: int = 10) -> dict[str, dict[str, list]]:
        """
        Histogram bin edges + counts for each numeric column.
        Returns: {col: {"bin_edges": [...], "counts": [...]}, ...}
        """
        histograms: dict[str, dict[str, list]] = {}
        for col in self._numeric_df.columns:
            series = self._numeric_df[col].dropna()
            if series.empty or series.nunique() <= 1:
                continue
            counts, bin_edges = np.histogram(series, bins=bins)
            histograms[col] = {
                "bin_edges": [round(float(edge), 3) for edge in bin_edges],
                "counts": [int(c) for c in counts],
            }
        return histograms

    def boxplot_stats(self, max_outlier_points: int = 50) -> dict[str, dict[str, Any]]:
        """
        Five-number summary (min/Q1/median/Q3/max) plus IQR-based whiskers
        and outlier points per numeric column, for boxplot visualization.
        Whiskers match the "iqr" method used by detect_outliers().
        """
        stats: dict[str, dict[str, Any]] = {}
        for col in self._numeric_df.columns:
            series = self._numeric_df[col].dropna()
            if series.empty:
                continue

            q1, q3, lower_fence, upper_fence = self._calculate_iqr_bounds(series)

            in_range = series[(series >= lower_fence) & (series <= upper_fence)]
            outliers = series[(series < lower_fence) | (series > upper_fence)]

            whisker_low = in_range.min() if not in_range.empty else series.min()
            whisker_high = in_range.max() if not in_range.empty else series.max()

            stats[col] = {
                "min": round(float(series.min()), 3),
                "q1": round(float(q1), 3),
                "median": round(float(series.median()), 3),
                "q3": round(float(q3), 3),
                "max": round(float(series.max()), 3),
                "whisker_low": round(float(whisker_low), 3),
                "whisker_high": round(float(whisker_high), 3),
                "outliers": [round(float(v), 3) for v in outliers.head(max_outlier_points).tolist()],
            }
        return stats

    def detect_date_like_columns(self, sample_size: int = 20) -> list[str]:
        """
        Flags object/string columns whose values look like dates,
        so they can be considered for parsing as datetime.
        """
        candidates: list[str] = []
        object_cols = self.df.select_dtypes(include=["object", "string"]).columns

        for col in object_cols:
            sample = self.df[col].dropna().astype(str).head(sample_size)
            if sample.empty:
                continue

            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            success_ratio = parsed.notna().mean()

            if success_ratio >= self.DATETIME_SUCCESS_RATIO:
                candidates.append(col)

        return candidates

    def memory_usage(self) -> dict[str, float]:
        """Per-column memory footprint in KB, useful before profiling huge files."""
        usage = self.df.memory_usage(deep=True)
        return {
            col: round(usage[col] / 1024, 2)
            for col in self.df.columns
        }

    def detect_mixed_type_columns(self) -> list[str]:
        """
        Flags object columns holding more than one Python type
        (e.g. a column with both strings and ints), a common
        source of silent bugs downstream.
        """
        mixed: list[str] = []
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            types_seen = self.df[col].dropna().map(type).nunique()
            if types_seen > 1:
                mixed.append(col)
        return mixed

    def text_column_stats(self) -> dict[str, dict[str, float]]:
        """
        Length stats for string columns, surfacing empty/whitespace-only
        values and unusually long/short entries.
        """
        stats: dict[str, dict[str, float]] = {}
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            series = self.df[col].dropna().astype(str)
            if series.empty:
                continue
            lengths = series.str.len()
            blank_count = series.str.strip().eq("").sum()
            stats[col] = {
                "avg_length": round(float(lengths.mean()), 1),
                "min_length": int(lengths.min()),
                "max_length": int(lengths.max()),
                "blank_or_whitespace_only": int(blank_count),
            }
        return stats

    def detect_negative_in_nonnegative_columns(self) -> list[str]:
        """
        Flags numeric columns whose name suggests they should never be
        negative (count, age, price, quantity, etc.) but contain negatives.
        """
        flagged: list[str] = []
        for col in self._numeric_df.columns:
            if any(kw in col.lower() for kw in self.NONNEGATIVE_KEYWORDS):
                if (self._numeric_df[col].dropna() < 0).any():
                    flagged.append(col)
        return flagged

    def health_score(self, rules: HealthScoreRules | None = None) -> dict[str, Any]:
        """
        Overall 0-100 data-quality score: 100 minus a documented, capped
        deduction per issue category (see HEALTH_SCORE_MAX_DEDUCTIONS).
        Deliberately inspectable rather than a black box: "breakdown" shows
        exactly how many points each category cost, so the number can be
        explained, not just quoted.

        `rules` overrides the default per-category weights/severities and
        adds per-column severity overrides (e.g. "negative_values is a
        failure specifically on the price column, a warning everywhere
        else"); see src/data_detective/rules.py and load_rules(). Omitting
        it (the default) reproduces today's fixed scoring exactly:
        health_score() and health_score(rules=DataProfiler.DEFAULT_RULES)
        always agree, since DEFAULT_RULES *is* what this falls back to.
        """
        rules = rules or self.DEFAULT_RULES
        total_rows = len(self.df)
        breakdown: dict[str, float] = {}
        failures: set[str] = set()

        def weight(category: str) -> float:
            return rules.categories[category].weight

        def flag_failure(category: str, affected_columns: list[str] | None = None) -> None:
            """Marks `category` as a failure if its resolved severity is
            "failure", either category-wide or via a per-column override
            on one of `affected_columns`. Only called after confirming the
            category actually deducted something."""
            rule = rules.categories[category]
            if rule.severity == "failure":
                failures.add(category)
                return
            for column in affected_columns or []:
                override = rules.override_for(category, column)
                if override and (override.severity or rule.severity) == "failure":
                    failures.add(category)
                    return

        # Missing values: blends the worst single column (70% weight, so one
        # badly broken column is penalized even if every other column is
        # clean, matching generate_insights() flagging any column over 30%
        # on its own) with the overall average (30% weight, so widespread
        # moderate missingness still registers even with no single outlier
        # column).
        missing_pcts_by_col = self.missing_percentage()
        missing_pcts = list(missing_pcts_by_col.values())
        avg_missing_ratio = (sum(missing_pcts) / len(missing_pcts) / 100) if missing_pcts else 0.0
        max_missing_ratio = (max(missing_pcts) / 100) if missing_pcts else 0.0
        missing_ratio = (
            self.MISSING_VALUES_WORST_COLUMN_WEIGHT * max_missing_ratio
            + self.MISSING_VALUES_AVERAGE_WEIGHT * avg_missing_ratio
        )
        missing_values_cap = weight("missing_values")
        breakdown["missing_values"] = round(min(missing_values_cap, missing_ratio * missing_values_cap), 1)
        if breakdown["missing_values"] > 0:
            flag_failure("missing_values", [col for col, pct in missing_pcts_by_col.items() if pct > 0])

        # Duplicate rows: ratio of duplicated rows to total rows maps
        # directly onto the cap.
        dup_row_ratio = (self.duplicate_rows() / total_rows) if total_rows else 0.0
        duplicate_rows_cap = weight("duplicate_rows")
        breakdown["duplicate_rows"] = round(min(duplicate_rows_cap, dup_row_ratio * duplicate_rows_cap), 1)
        if breakdown["duplicate_rows"] > 0:
            flag_failure("duplicate_rows")

        # Outliers: genuinely extreme values (MAD method) are only ever a
        # small tail of any column by construction, so raw cell-ratio needs
        # a large scale to register at all; a 1% outlier-cell rate alone
        # maxes the deduction.
        outlier_counts = self.detect_outliers(method="mad")
        total_numeric_cells = int(self._numeric_df.notna().sum().sum())
        outlier_ratio = (sum(outlier_counts.values()) / total_numeric_cells) if total_numeric_cells else 0.0
        outliers_cap = weight("outliers")
        breakdown["outliers"] = round(
            min(outliers_cap, outlier_ratio * self.OUTLIER_CELL_RATIO_SCALE * outliers_cap), 1
        )
        if breakdown["outliers"] > 0:
            flag_failure("outliers", [col for col, count in outlier_counts.items() if count > 0])

        # Duplicate columns, constant columns, mixed-type columns, and
        # unexpected negatives are flat points per occurrence, capped: each
        # instance is a concrete, discrete issue rather than a proportion.
        duplicate_column_pairs = self.detect_duplicate_columns()
        duplicate_columns_cap = weight("duplicate_columns")
        breakdown["duplicate_columns"] = round(
            min(duplicate_columns_cap, len(duplicate_column_pairs) * self.DUPLICATE_COLUMN_POINTS_PER_OCCURRENCE), 1
        )
        if breakdown["duplicate_columns"] > 0:
            flag_failure("duplicate_columns", [col for pair in duplicate_column_pairs for col in pair])

        constant_cols = self.detect_constant_columns()
        constant_columns_cap = weight("constant_columns")
        breakdown["constant_columns"] = round(
            min(constant_columns_cap, len(constant_cols) * self.CONSTANT_COLUMN_POINTS_PER_OCCURRENCE), 1
        )
        if breakdown["constant_columns"] > 0:
            flag_failure("constant_columns", constant_cols)

        mixed_type_cols = self.detect_mixed_type_columns()
        mixed_type_columns_cap = weight("mixed_type_columns")
        breakdown["mixed_type_columns"] = round(
            min(mixed_type_columns_cap, len(mixed_type_cols) * self.MIXED_TYPE_POINTS_PER_OCCURRENCE), 1
        )
        if breakdown["mixed_type_columns"] > 0:
            flag_failure("mixed_type_columns", mixed_type_cols)

        negative_cols = self.detect_negative_in_nonnegative_columns()
        negative_values_cap = weight("negative_values")
        breakdown["negative_values"] = round(
            min(negative_values_cap, len(negative_cols) * self.NEGATIVE_VALUES_POINTS_PER_OCCURRENCE), 1
        )
        if breakdown["negative_values"] > 0:
            flag_failure("negative_values", negative_cols)

        # Skewed distributions: fraction of numeric columns heavily skewed,
        # scaled 2x before capping so half the numeric columns being skewed
        # maxes the deduction.
        shapes = self.distribution_shape()
        skewed_cols = [col for col, s in shapes.items() if abs(s["skewness"]) > self.SKEWNESS_THRESHOLD]
        skewed_ratio = (len(skewed_cols) / len(shapes)) if shapes else 0.0
        skewed_distributions_cap = weight("skewed_distributions")
        breakdown["skewed_distributions"] = round(
            min(skewed_distributions_cap, skewed_ratio * self.SKEWED_RATIO_SCALE * skewed_distributions_cap), 1
        )
        if breakdown["skewed_distributions"] > 0:
            flag_failure("skewed_distributions", skewed_cols)

        # Correlated (redundant) columns: flat points per pair, capped.
        correlated_pairs = self.detect_correlated_columns()
        correlated_columns_cap = weight("correlated_columns")
        breakdown["correlated_columns"] = round(
            min(correlated_columns_cap, len(correlated_pairs) * self.CORRELATED_PAIR_POINTS), 1
        )
        if breakdown["correlated_columns"] > 0:
            flag_failure("correlated_columns", [col for a, b, _ in correlated_pairs for col in (a, b)])

        # Near-constant and date-like columns: capped at 0 by default (see
        # HEALTH_SCORE_MAX_DEDUCTIONS/DEFAULT_RULES), so skip the detector
        # call entirely rather than computing it just to multiply by zero.
        # Both detectors already run once, unconditionally, in
        # run_full_profile() and are surfaced there and in
        # generate_insights() regardless of scoring.
        near_constant_cap = weight("near_constant_columns")
        if near_constant_cap > 0:
            near_constant_cols = self.detect_near_constant_columns()
            breakdown["near_constant_columns"] = round(
                min(near_constant_cap, len(near_constant_cols) * self.NEAR_CONSTANT_COLUMN_POINTS_PER_OCCURRENCE), 1
            )
            if breakdown["near_constant_columns"] > 0:
                flag_failure("near_constant_columns", near_constant_cols)
        else:
            breakdown["near_constant_columns"] = 0.0

        date_like_cap = weight("date_like_columns")
        if date_like_cap > 0:
            date_like_cols = self.detect_date_like_columns()
            breakdown["date_like_columns"] = round(
                min(date_like_cap, len(date_like_cols) * self.DATE_LIKE_COLUMN_POINTS_PER_OCCURRENCE), 1
            )
            if breakdown["date_like_columns"] > 0:
                flag_failure("date_like_columns", date_like_cols)
        else:
            breakdown["date_like_columns"] = 0.0

        score = max(0, round(100 - sum(breakdown.values())))
        grade = next(label for threshold, label in self.HEALTH_SCORE_GRADES if score >= threshold)

        informational_categories = sorted(name for name, rule in rules.categories.items() if rule.weight == 0)

        return {
            "score": score,
            "grade": grade,
            "breakdown": breakdown,
            "informational_categories": informational_categories,
            "failures": sorted(failures),
        }

    def generate_insights(self, outlier_method: str = "mad") -> list[str]:
        """
        Human-readable detective conclusions.
        """
        insights: list[str] = []

        # Missing data insight
        missing_pct = self.missing_percentage()
        for col, pct in missing_pct.items():
            if pct > 30:
                insights.append(f"🚨 Column '{col}' has high missingness ({pct}%).")

        # Constant columns
        constants = self.detect_constant_columns()
        for col in constants:
            insights.append(f"⚠️ Column '{col}' is constant (no variation).")

        # Near-constant columns
        for col in self.detect_near_constant_columns():
            insights.append(f"🔁 Column '{col}' is nearly constant (one value dominates almost all rows).")

        # Possible modeling target
        for col in self.detect_possible_target_columns():
            insights.append(f"🎯 Column '{col}' looks like it could be the modeling target.")

        # High cardinality (possible ID)
        ids = self.detect_high_cardinality()
        for col in ids:
            insights.append(f"🆔 Column '{col}' looks like an ID (very high uniqueness).")

        # Outliers
        outliers = self.detect_outliers(method=outlier_method)
        for col, count in outliers.items():
            if count > 0:
                insights.append(
                    f"📊 Column '{col}' has {count} potential outlier(s) ({outlier_method.upper()} method)."
                )

        # Duplicate columns
        dup_cols = self.detect_duplicate_columns()
        for col_a, col_b in dup_cols:
            insights.append(f"🧬 Columns '{col_a}' and '{col_b}' are identical.")

        # Correlated columns
        correlated = self.detect_correlated_columns()
        for col_a, col_b, value in correlated:
            insights.append(f"🔗 Columns '{col_a}' and '{col_b}' are highly correlated ({value}).")

        # Date-like columns
        date_like = self.detect_date_like_columns()
        for col in date_like:
            insights.append(f"📅 Column '{col}' looks like it contains dates (consider parsing as datetime).")

        # Mixed-type columns
        for col in self.detect_mixed_type_columns():
            insights.append(f"🧩 Column '{col}' contains mixed data types.")

        # Negative values in non-negative columns
        for col in self.detect_negative_in_nonnegative_columns():
            insights.append(f"➖ Column '{col}' contains unexpected negative values.")

        # Skewed distributions
        for col, shape in self.distribution_shape().items():
            if abs(shape["skewness"]) > self.SKEWNESS_THRESHOLD:
                insights.append(f"📐 Column '{col}' is heavily skewed (skew={shape['skewness']}).")

        return insights

    def run_full_profile(self, outlier_method: str = "mad", rules: HealthScoreRules | None = None) -> dict[str, Any]:
        return {
            "health_score": self.health_score(rules=rules),
            "shape": self.shape(),
            "column_types": self.column_types(),
            "missing_values": self.missing_values(),
            "missing_percentage": self.missing_percentage(),
            "duplicates": self.duplicate_rows(),
            "unique_counts": self.unique_counts(),
            "constant_columns": self.detect_constant_columns(),
            "near_constant_columns": self.detect_near_constant_columns(),
            "possible_target_columns": self.detect_possible_target_columns(),
            "high_cardinality_columns": self.detect_high_cardinality(),
            "outliers_iqr": self.detect_outliers(method="iqr"),
            "outliers_mad": self.detect_outliers(method="mad"),
            "distribution_shape": self.distribution_shape(),
            "duplicate_columns": self.detect_duplicate_columns(),
            "correlated_columns": self.detect_correlated_columns(),
            "correlation_matrix": self.correlation_matrix(),
            "histogram_data": self.histogram_data(),
            "boxplot_stats": self.boxplot_stats(),
            "date_like_columns": self.detect_date_like_columns(),
            "mixed_type_columns": self.detect_mixed_type_columns(),
            "text_column_stats": self.text_column_stats(),
            "memory_usage_kb": self.memory_usage(),
            "negative_in_nonnegative_columns": self.detect_negative_in_nonnegative_columns(),
            "insights": self.generate_insights(outlier_method=outlier_method),
            "partial_analysis": self.partial_analysis_notices(),
        }
