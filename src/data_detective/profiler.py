import pandas as pd
import numpy as np
from functools import cached_property


class DataProfiler:
    """
    Advanced Data Detective engine.
    Adds statistical intelligence + anomaly detection.
    """

    HIGH_CARDINALITY_THRESHOLD = 0.9
    CORRELATION_THRESHOLD = 0.9
    MAD_Z_CONSTANT = 0.6745
    IQR_MULTIPLIER = 1.5
    MAD_OUTLIER_THRESHOLD = 3.5
    DATETIME_SUCCESS_RATIO = 0.8
    SKEWNESS_THRESHOLD = 2.0
    NONNEGATIVE_KEYWORDS = ("count", "age", "price", "quantity", "amount", "qty", "total")

    def __init__(self, df: pd.DataFrame):
        self.df = df

    # -------------------------
    # CACHED INTERNAL STATE (computed once, reused everywhere)
    # -------------------------

    @cached_property
    def _numeric_df(self):
        return self.df.select_dtypes(include=[np.number])

    @cached_property
    def _nunique(self):
        return self.df.nunique()

    @cached_property
    def _null_counts(self):
        return self.df.isnull().sum()

    @cached_property
    def _quantiles(self):
        """Q1/Q3 for all numeric columns computed once."""
        if self._numeric_df.empty:
            return pd.DataFrame()
        return self._numeric_df.quantile([0.25, 0.75])

    # -------------------------
    # BASIC STRUCTURE
    # -------------------------

    def shape(self):
        return {"rows": self.df.shape[0], "columns": self.df.shape[1]}

    def column_types(self):
        return self.df.dtypes.astype(str).to_dict()

    def missing_values(self):
        return self._null_counts.to_dict()

    def missing_percentage(self):
        if len(self.df) == 0:
            return {}
        return (self._null_counts / len(self.df) * 100).round(2).to_dict()

    def duplicate_rows(self):
        return int(self.df.duplicated().sum())

    def unique_counts(self):
        return self._nunique.to_dict()

    # -------------------------
    # INTELLIGENCE LAYER
    # -------------------------

    def detect_constant_columns(self):
        return self._nunique[self._nunique <= 1].index.tolist()

    def detect_high_cardinality(self, threshold=None, min_unique=10):
        if threshold is None:
            threshold = self.HIGH_CARDINALITY_THRESHOLD
        if len(self.df) == 0:
            return []

        ratio = self._nunique / len(self.df)
        mask = (ratio >= threshold) & (self._nunique >= min_unique)
        return self._nunique[mask].index.tolist()

    def _calculate_iqr_bounds(self, series):
        """Returns (q1, q3, lower_fence, upper_fence) for a numeric series."""
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower_fence = q1 - self.IQR_MULTIPLIER * iqr
        upper_fence = q3 + self.IQR_MULTIPLIER * iqr
        return q1, q3, lower_fence, upper_fence

    def detect_outliers(self, method="iqr"):
        """
        method: "iqr" (default) or "mad" (robust z-score, better for skewed data)
        Returns count per column.
        """
        outliers = {}

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

    def distribution_shape(self):
        """
        Skewness and kurtosis for numeric columns, flagging columns where
        the mean/IQR-based stats alone would be misleading.
        """
        shape = {}
        for col in self._numeric_df.columns:
            series = self._numeric_df[col].dropna()
            if len(series) < 3:
                continue
            shape[col] = {
                "skewness": round(float(series.skew()), 3),
                "kurtosis": round(float(series.kurt()), 3),
            }
        return shape

    def detect_duplicate_columns(self):
        """
        Finds pairs of columns that are exactly identical.
        Returns a list of (col_a, col_b) tuples.
        """
        duplicates = []
        cols = list(self.df.columns)

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col_a, col_b = cols[i], cols[j]
                if self.df[col_a].equals(self.df[col_b]):
                    duplicates.append((col_a, col_b))

        return duplicates

    def detect_correlated_columns(self, threshold=None):
        """
        Finds pairs of numeric columns with correlation above threshold.
        """
        if threshold is None:
            threshold = self.CORRELATION_THRESHOLD
        if self._numeric_df.shape[1] < 2:
            return []

        corr_matrix = self._numeric_df.corr().abs()
        pairs = []
        cols = corr_matrix.columns

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                value = corr_matrix.iloc[i, j]
                if pd.notna(value) and value >= threshold:
                    pairs.append((cols[i], cols[j], round(float(value), 3)))

        return pairs

    def correlation_matrix(self):
        """
        Full pairwise correlation matrix for numeric columns, as a
        nested dict: {col_a: {col_b: correlation_value, ...}, ...}.
        Used for heatmap visualization.
        """
        if self._numeric_df.shape[1] < 2:
            return {}

        corr = self._numeric_df.corr().round(3)
        # Replace NaN (e.g. constant columns) with 0 so it's JSON-safe.
        corr = corr.fillna(0)
        return {col: corr[col].to_dict() for col in corr.columns}

    def histogram_data(self, bins=10):
        """
        Histogram bin edges + counts for each numeric column.
        Returns: {col: {"bin_edges": [...], "counts": [...]}, ...}
        """
        histograms = {}
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

    def boxplot_stats(self, max_outlier_points=50):
        """
        Five-number summary (min/Q1/median/Q3/max) plus IQR-based whiskers
        and outlier points per numeric column, for boxplot visualization.
        Whiskers match the "iqr" method used by detect_outliers().
        """
        stats = {}
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

    def detect_date_like_columns(self, sample_size=20):
        """
        Flags object/string columns whose values look like dates,
        so they can be considered for parsing as datetime.
        """
        candidates = []
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

    def memory_usage(self):
        """Per-column memory footprint in KB, useful before profiling huge files."""
        usage = self.df.memory_usage(deep=True)
        return {
            col: round(usage[col] / 1024, 2)
            for col in self.df.columns
        }

    def detect_mixed_type_columns(self):
        """
        Flags object columns holding more than one Python type
        (e.g. a column with both strings and ints), a common
        source of silent bugs downstream.
        """
        mixed = []
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            types_seen = self.df[col].dropna().map(type).nunique()
            if types_seen > 1:
                mixed.append(col)
        return mixed

    def text_column_stats(self):
        """
        Length stats for string columns, surfacing empty/whitespace-only
        values and unusually long/short entries.
        """
        stats = {}
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

    def detect_negative_in_nonnegative_columns(self):
        """
        Flags numeric columns whose name suggests they should never be
        negative (count, age, price, quantity, etc.) but contain negatives.
        """
        flagged = []
        for col in self._numeric_df.columns:
            if any(kw in col.lower() for kw in self.NONNEGATIVE_KEYWORDS):
                if (self._numeric_df[col].dropna() < 0).any():
                    flagged.append(col)
        return flagged

    def generate_insights(self, outlier_method="mad"):
        """
        Human-readable detective conclusions.
        """
        insights = []

        # Missing data insight
        missing_pct = self.missing_percentage()
        for col, pct in missing_pct.items():
            if pct > 30:
                insights.append(f"🚨 Column '{col}' has high missingness ({pct}%).")

        # Constant columns
        constants = self.detect_constant_columns()
        for col in constants:
            insights.append(f"⚠️ Column '{col}' is constant (no variation).")

        # High cardinality (possible ID)
        ids = self.detect_high_cardinality()
        for col in ids:
            insights.append(f"🆔 Column '{col}' looks like an ID (very high uniqueness).")

        # Outliers
        outliers = self.detect_outliers(method=outlier_method)
        for col, count in outliers.items():
            if count > 0:
                insights.append(f"📊 Column '{col}' has {count} potential outlier(s) ({outlier_method.upper()} method).")

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

    def run_full_profile(self, outlier_method="mad"):
        return {
            "shape": self.shape(),
            "column_types": self.column_types(),
            "missing_values": self.missing_values(),
            "missing_percentage": self.missing_percentage(),
            "duplicates": self.duplicate_rows(),
            "unique_counts": self.unique_counts(),
            "constant_columns": self.detect_constant_columns(),
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
            "insights": self.generate_insights(outlier_method=outlier_method)
        }