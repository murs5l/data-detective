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


def test_high_cardinality_excludes_continuous_numeric_measures():
    # TotalPay-style columns are unique per-row because they're continuous
    # measurements, not because they're identifiers. They shouldn't be
    # flagged as "looks like an ID".
    df = pd.DataFrame({
        "TotalPay": [round(50000 + i * 731.42, 2) for i in range(50)],
        "TotalPayBenefits": [round(55000 + i * 812.11, 2) for i in range(50)],
    })
    profiler = DataProfiler(df)
    flagged = profiler.detect_high_cardinality()
    assert "TotalPay" not in flagged
    assert "TotalPayBenefits" not in flagged


def test_high_cardinality_flags_id_like_name():
    df = pd.DataFrame({"employee_id": list(range(1000, 1050))})
    profiler = DataProfiler(df)
    assert "employee_id" in profiler.detect_high_cardinality()


def test_high_cardinality_flags_sequential_integer_without_id_name():
    # A gapless run of integers (1..N) is the classic shape of an
    # auto-increment key or row index, even without "id" in the name.
    df = pd.DataFrame({"row_number": list(range(1, 51))})
    profiler = DataProfiler(df)
    assert "row_number" in profiler.detect_high_cardinality()


def test_high_cardinality_still_flags_unique_text_column():
    df = pd.DataFrame({"email": [f"user{i}@example.com" for i in range(50)]})
    profiler = DataProfiler(df)
    assert "email" in profiler.detect_high_cardinality()


def test_high_cardinality_excludes_continuous_measures_from_insights():
    df = pd.DataFrame({
        "TotalPay": [round(50000 + i * 731.42, 2) for i in range(50)],
    })
    profiler = DataProfiler(df)
    insights = profiler.generate_insights()
    assert not any("TotalPay" in i and "ID" in i for i in insights)


def test_near_constant_column_flagged_but_not_as_fully_constant():
    df = pd.DataFrame({
        "status": ["active"] * 97 + ["inactive"] * 3,
        "normal": list(range(100)),
    })
    profiler = DataProfiler(df)
    assert "status" in profiler.detect_near_constant_columns()
    assert "status" not in profiler.detect_constant_columns()
    assert "normal" not in profiler.detect_near_constant_columns()


def test_near_constant_excludes_fully_constant_columns():
    # A truly constant column shouldn't double-count as "near-constant" too.
    df = pd.DataFrame({"c": [1] * 20})
    profiler = DataProfiler(df)
    assert "c" in profiler.detect_constant_columns()
    assert "c" not in profiler.detect_near_constant_columns()


def test_near_constant_below_threshold_not_flagged():
    df = pd.DataFrame({"mostly_varied": ["a"] * 80 + ["b"] * 20})
    profiler = DataProfiler(df)
    assert "mostly_varied" not in profiler.detect_near_constant_columns()


def test_possible_target_column_detected_by_name():
    df = pd.DataFrame({"age": [1, 2, 3], "income": [4, 5, 6], "churn": [0, 1, 0]})
    profiler = DataProfiler(df)
    assert profiler.detect_possible_target_columns() == ["churn"]


def test_possible_target_column_bare_y_detected():
    df = pd.DataFrame({"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [0, 1, 0]})
    profiler = DataProfiler(df)
    assert profiler.detect_possible_target_columns() == ["y"]


def test_possible_target_column_no_false_positive_on_y_as_word_component():
    # "y_coordinate" contains "y" as a whole word after splitting, but it's
    # a spatial axis, not an ML target; only a column named exactly "y"
    # should match.
    df = pd.DataFrame({"TotalPay": [1, 2, 3], "y_coordinate": [4, 5, 6]})
    profiler = DataProfiler(df)
    assert profiler.detect_possible_target_columns() == []


def test_possible_target_column_none_found_returns_empty_list():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    profiler = DataProfiler(df)
    assert profiler.detect_possible_target_columns() == []


def test_run_full_profile_includes_new_detector_keys():
    df = pd.DataFrame({"a": [1, 2, 3], "target": [0, 1, 0]})
    report = DataProfiler(df).run_full_profile()
    assert "near_constant_columns" in report
    assert "possible_target_columns" in report
    assert report["possible_target_columns"] == ["target"]


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
        "histogram_data", "boxplot_stats", "date_like_columns",
        "mixed_type_columns", "text_column_stats",
        "memory_usage_kb", "negative_in_nonnegative_columns", "insights",
    }
    assert expected_keys.issubset(report.keys())


def test_correlation_matrix_shape():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8], "c": ["x", "y", "x", "y"]})
    profiler = DataProfiler(df)
    matrix = profiler.correlation_matrix()
    assert "a" in matrix and "b" in matrix
    assert "c" not in matrix
    assert matrix["a"]["a"] == 1.0


def test_correlation_matrix_single_numeric_column():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    profiler = DataProfiler(df)
    assert profiler.correlation_matrix() == {}


def test_histogram_data_basic():
    df = pd.DataFrame({"a": list(range(100))})
    profiler = DataProfiler(df)
    hist = profiler.histogram_data(bins=5)
    assert "a" in hist
    assert len(hist["a"]["counts"]) == 5
    assert len(hist["a"]["bin_edges"]) == 6
    assert sum(hist["a"]["counts"]) == 100


def test_histogram_data_skips_constant_column():
    df = pd.DataFrame({"constant": [5, 5, 5, 5]})
    profiler = DataProfiler(df)
    assert profiler.histogram_data() == {}


def test_boxplot_stats_basic():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    profiler = DataProfiler(df)
    stats = profiler.boxplot_stats()

    assert "a" in stats
    box = stats["a"]
    assert box["min"] == 1
    assert box["max"] == 10
    assert box["median"] == pytest.approx(5.5)
    assert box["q1"] < box["median"] < box["q3"]
    assert box["outliers"] == []


def test_boxplot_stats_flags_outliers():
    df = pd.DataFrame({"a": [10, 12, 11, 13, 12, 11, 10, 1000]})
    profiler = DataProfiler(df)
    stats = profiler.boxplot_stats()

    assert 1000 in stats["a"]["outliers"]
    assert stats["a"]["whisker_high"] < 1000


def test_boxplot_stats_ignores_non_numeric_columns():
    df = pd.DataFrame({"c": ["x", "y", "z"]})
    profiler = DataProfiler(df)
    assert profiler.boxplot_stats() == {}


def test_health_score_clean_data_scores_high():
    df = pd.DataFrame({
        "id": range(1, 101),
        "value": [i * 1.5 for i in range(100)],
        "category": (["A", "B", "C"] * 34)[:100],
    })
    result = DataProfiler(df).health_score()

    assert result["score"] >= 90
    assert result["grade"] == "Excellent"
    assert set(result["breakdown"]) == set(DataProfiler.HEALTH_SCORE_MAX_DEDUCTIONS)


def test_health_score_empty_df_is_perfect():
    result = DataProfiler(pd.DataFrame()).health_score()
    assert result["score"] == 100
    assert result["grade"] == "Excellent"


def test_health_score_penalizes_a_single_severely_missing_column():
    # One column mostly missing, everything else clean: averaging across
    # all columns must not dilute this away to nothing.
    df = pd.DataFrame({
        "a": [None] * 40 + list(range(60)),
        "b": list(range(100)),
        "c": list(range(100)),
    })
    result = DataProfiler(df).health_score()
    assert result["breakdown"]["missing_values"] > 5


def test_health_score_flags_duplicate_and_constant_columns():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "a_copy": [1, 2, 3, 4, 5],
        "constant": [1, 1, 1, 1, 1],
    })
    result = DataProfiler(df).health_score()
    assert result["breakdown"]["duplicate_columns"] > 0
    assert result["breakdown"]["constant_columns"] > 0
    assert result["score"] < 100


def test_health_score_worse_data_scores_lower_than_better_data():
    clean = pd.DataFrame({"a": range(100), "b": range(100)})
    messy = pd.DataFrame({
        "a": [None] * 50 + list(range(50)),
        "a_copy": [None] * 50 + list(range(50)),
        "b": [1] * 100,
    })
    clean_score = DataProfiler(clean).health_score()["score"]
    messy_score = DataProfiler(messy).health_score()["score"]
    assert messy_score < clean_score


def test_health_score_grade_matches_score_thresholds():
    for score, expected_grade in [(95, "Excellent"), (80, "Good"), (65, "Fair"), (45, "Poor"), (10, "Critical")]:
        grade = next(label for threshold, label in DataProfiler.HEALTH_SCORE_GRADES if score >= threshold)
        assert grade == expected_grade


def test_run_full_profile_includes_health_score():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    report = DataProfiler(df).run_full_profile()
    assert "health_score" in report
    assert 0 <= report["health_score"]["score"] <= 100
