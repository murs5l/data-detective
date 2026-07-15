import pandas as pd
import pytest

from data_detective.html_report import generate_html_report
from data_detective.profiler import DataProfiler


@pytest.fixture
def report():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "b": [2, 4, 6, 8, 10],
        "c": ["x", "y", "x", "y", "z"],
    })
    return DataProfiler(df).run_full_profile()


def test_html_report_includes_correlation_heatmap(tmp_path, report):
    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Correlation Heatmap" in html
    assert "heatmap-table" in html
    assert "heatmap-cell" in html


def test_html_report_includes_column_explorer(tmp_path, report):
    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Column Explorer" in html
    assert "column-select" in html
    assert "hist-bar" in html
    assert "box-plot-svg" in html
    assert "box-rect" in html
    assert "stat-chip" in html


def test_html_report_explorer_excludes_id_like_and_constant_columns(tmp_path):
    df = pd.DataFrame({
        "id": list(range(1, 21)),
        "constant": [1] * 20,
        "value": [10, 12, 11, 13, 14, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 100],
    })
    report = DataProfiler(df).run_full_profile()

    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert 'data-column="value"' in html
    assert 'data-column="id"' not in html
    assert 'data-column="constant"' not in html
    assert "left out here" in html


def test_html_report_insights_lead_and_technical_detail_is_collapsed(tmp_path, report):
    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    # Insights must render before the raw technical tables, not after, so a
    # reader sees plain-English findings before a wall of numbers.
    insights_pos = html.index(">🧠 Insights<")
    tech_report_pos = html.index("Full technical report")
    assert insights_pos < tech_report_pos

    # The technical tables must be tucked behind a native <details> toggle,
    # not always fully expanded.
    assert "<details" in html
    assert 'class="box details-card"' in html


def test_html_report_handles_no_numeric_columns(tmp_path):
    df = pd.DataFrame({"c": ["x", "y", "z"]})
    report = DataProfiler(df).run_full_profile()

    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Not enough numeric columns for a heatmap." in html
    assert "No numeric columns to chart." in html
