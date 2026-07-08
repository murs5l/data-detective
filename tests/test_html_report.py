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


def test_html_report_includes_histograms(tmp_path, report):
    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Histograms" in html
    assert "hist-bar" in html


def test_html_report_includes_boxplots(tmp_path, report):
    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Boxplots" in html
    assert "box-plot-svg" in html
    assert "box-rect" in html


def test_html_report_handles_no_numeric_columns(tmp_path):
    df = pd.DataFrame({"c": ["x", "y", "z"]})
    report = DataProfiler(df).run_full_profile()

    output_path = tmp_path / "report.html"
    generate_html_report(report, output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")

    assert "Not enough numeric columns for a heatmap." in html
    assert "No numeric columns to chart." in html
