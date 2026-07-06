import pandas as pd
import numpy as np


class DataProfiler:
    """
    Advanced Data Detective engine.
    Adds statistical intelligence + anomaly detection.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    # -------------------------
    # BASIC STRUCTURE
    # -------------------------

    def shape(self):
        return {"rows": self.df.shape[0], "columns": self.df.shape[1]}

    def column_types(self):
        return self.df.dtypes.astype(str).to_dict()

    def missing_values(self):
        return self.df.isnull().sum().to_dict()

    def missing_percentage(self):
        return (self.df.isnull().mean() * 100).round(2).to_dict()

    def duplicate_rows(self):
        return int(self.df.duplicated().sum())

    def unique_counts(self):
        return self.df.nunique().to_dict()

    # -------------------------
    # INTELLIGENCE LAYER
    # -------------------------

    def detect_constant_columns(self):
        return [
            col for col in self.df.columns
            if self.df[col].nunique() <= 1
        ]

    def detect_high_cardinality(self, threshold=0.9, min_unique=10):
        if len(self.df) == 0:
            return []

        result = []

        for col in self.df.columns:
            unique_count = self.df[col].nunique()
            unique_ratio = unique_count / len(self.df)

            if unique_ratio >= threshold and unique_count >= min_unique:
                result.append(col)

        return result

    def detect_outliers(self):
        """
        IQR-based outlier detection for numeric columns.
        Returns count per column.
        """
        outliers = {}

        numeric_df = self.df.select_dtypes(include=[np.number])

        for col in numeric_df.columns:
            q1 = numeric_df[col].quantile(0.25)
            q3 = numeric_df[col].quantile(0.75)
            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            count = ((numeric_df[col] < lower) | (numeric_df[col] > upper)).sum()
            outliers[col] = int(count)

        return outliers

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

    def detect_correlated_columns(self, threshold=0.9):
        """
        Finds pairs of numeric columns with correlation above threshold.
        """
        numeric_df = self.df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return []

        corr_matrix = numeric_df.corr().abs()
        pairs = []
        cols = corr_matrix.columns

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                value = corr_matrix.iloc[i, j]
                if pd.notna(value) and value >= threshold:
                    pairs.append((cols[i], cols[j], round(float(value), 3)))

        return pairs

    def detect_date_like_columns(self, sample_size=20):
        """
        Flags object/string columns whose values look like dates,
        so they can be considered for parsing as datetime.
        """
        candidates = []
        object_cols = self.df.select_dtypes(include=["object"]).columns

        for col in object_cols:
            sample = self.df[col].dropna().astype(str).head(sample_size)
            if sample.empty:
                continue

            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            success_ratio = parsed.notna().mean()

            if success_ratio >= 0.8:
                candidates.append(col)

        return candidates

    def generate_insights(self):
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
        outliers = self.detect_outliers()
        for col, count in outliers.items():
            if count > 0:
                insights.append(f"📊 Column '{col}' has {count} potential outlier(s).")

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

        return insights

    def run_full_profile(self):
        return {
            "shape": self.shape(),
            "column_types": self.column_types(),
            "missing_values": self.missing_values(),
            "missing_percentage": self.missing_percentage(),
            "duplicates": self.duplicate_rows(),
            "unique_counts": self.unique_counts(),
            "constant_columns": self.detect_constant_columns(),
            "high_cardinality_columns": self.detect_high_cardinality(),
            "outliers": self.detect_outliers(),
            "duplicate_columns": self.detect_duplicate_columns(),
            "correlated_columns": self.detect_correlated_columns(),
            "date_like_columns": self.detect_date_like_columns(),
            "insights": self.generate_insights()
        }