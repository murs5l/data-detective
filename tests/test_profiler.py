import pandas as pd
import pytest

from data_detective.profiler import DataProfiler


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "value": [10, 12, 11, 13, 1000],
        "constant_col": ["A", "A", "A", "A", "A"],
        "with_nulls": [1, None, 3, None, 5],
        "dup_of_value": [10, 12, 11, 13, 1000],
    })


def test_shape(sample_df):
    profiler = DataProfiler(sample_df)
    assert profiler.shape() == {"rows": 5, "columns": 5}


def test_missing_values(sample_df):
    profiler = DataProfiler(sample_df)
    missing = profiler.missing_values()
    assert missing["with_nulls"] == 2
    assert missing["id"] == 0


def test_duplicate_rows_none(sample_df):
    profiler = DataProfiler(sample_df)
    assert profiler.duplicate_rows() == 0


def test_constant_columns(sample_df):
    profiler = DataProfiler(sample_df)
    assert "constant_col" in profiler.detect_constant_columns()


def test_high_cardinality_empty_df():
    profiler = DataProfiler(pd.DataFrame())
    assert profiler.detect_high_cardinality() == []


def test_detect_outliers(sample_df):
    profiler = DataProfiler(sample_df)
    outliers = profiler.detect_outliers(method="iqr")
    assert outliers["value"] >= 1
    assert "constant_col" not in outliers


def test_detect_outliers_mad(sample_df):
    profiler = DataProfiler(sample_df)
    outliers = profiler.detect_outliers(method="mad")
    assert outliers["value"] >= 1


def test_duplicate_columns(sample_df):
    profiler = DataProfiler(sample_df)
    dup_pairs = profiler.detect_duplicate_columns()
    assert ("value", "dup_of_value") in dup_pairs or ("dup_of_value", "value") in dup_pairs


def test_correlated_columns(sample_df):
    profiler = DataProfiler(sample_df)
    correlated = profiler.detect_correlated_columns()
    assert any(pair[0] == "value" and pair[1] == "dup_of_value" for pair in correlated)


def test_date_like_columns():
    df = pd.DataFrame({
        "created_at": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "name": ["a", "b", "c"],
    })
    profiler = DataProfiler(df)
    assert "created_at" in profiler.detect_date_like_columns()


def test_mixed_type_columns_and_negative_detection():
    df = pd.DataFrame({
        "mixed": [1, "2", 3],
        "age": [10, -1, 12],
        "name": ["a", "b", "c"],
    })
    profiler = DataProfiler(df)
    assert "mixed" in profiler.detect_mixed_type_columns()
    assert "age" in profiler.detect_negative_in_nonnegative_columns()


def test_distribution_shape_and_memory_usage(sample_df):
    profiler = DataProfiler(sample_df)
    distribution = profiler.distribution_shape()
    memory = profiler.memory_usage()
    assert "value" in distribution
    assert "value" in memory


def test_generate_insights_mentions_outliers(sample_df):
    profiler = DataProfiler(sample_df)
    insights = profiler.generate_insights()
    assert any("outlier" in i for i in insights)


def test_run_full_profile_keys(sample_df):
    profiler = DataProfiler(sample_df)
    report = profiler.run_full_profile()
    expected_keys = {
        "shape", "column_types", "missing_values", "missing_percentage",
        "duplicates", "unique_counts", "constant_columns",
        "high_cardinality_columns", "outliers_iqr", "outliers_mad",
        "distribution_shape", "duplicate_columns", "correlated_columns",
        "date_like_columns", "mixed_type_columns", "text_column_stats",
        "memory_usage_kb", "negative_in_nonnegative_columns", "insights",
    }
    assert expected_keys.issubset(report.keys())
