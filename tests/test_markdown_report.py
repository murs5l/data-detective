import pandas as pd
import pytest

from data_detective.markdown_report import generate_markdown_report, render_markdown_report
from data_detective.profiler import DataProfiler


@pytest.fixture
def report():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "b": [2, 4, 6, 8, 10],
        "c": ["x", "y", "x", "y", "z"],
    })
    return DataProfiler(df).run_full_profile()


def test_render_markdown_report_includes_health_score_and_insights(report):
    md = render_markdown_report(report)

    assert "# 🕵️ Data Detective Report" in md
    assert "Data Health Score:" in md
    assert "## Insights" in md


def test_render_markdown_report_health_score_leads_insights(report):
    md = render_markdown_report(report)

    health_pos = md.index("Data Health Score:")
    insights_pos = md.index("## Insights")
    assert health_pos < insights_pos


def test_render_markdown_report_wraps_technical_detail_in_details_block(report):
    md = render_markdown_report(report)

    assert "<details>" in md
    assert "<summary>Full technical report</summary>" in md
    assert "</details>" in md
    # The technical section must come after the collapsible opens, so it's
    # actually inside the <details>, not floating outside it.
    details_pos = md.index("<summary>Full technical report</summary>")
    missing_values_pos = md.index("### Missing values")
    assert details_pos < missing_values_pos


def test_render_markdown_report_handles_no_insights():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    report = DataProfiler(df).run_full_profile()
    # Force an empty insights list to exercise the "clean data" branch,
    # regardless of what this particular tiny dataset happens to trigger.
    report["insights"] = []

    md = render_markdown_report(report)
    assert "No notable insights" in md


def test_render_markdown_report_correlation_matrix_table(report):
    md = render_markdown_report(report)
    assert "### Correlation matrix" in md
    assert "| **a** |" in md


def test_render_markdown_report_no_numeric_columns_correlation_fallback():
    df = pd.DataFrame({"c": ["x", "y", "z"]})
    report = DataProfiler(df).run_full_profile()
    md = render_markdown_report(report)
    assert "Not enough numeric columns for a correlation matrix." in md


def test_generate_markdown_report_writes_file(tmp_path, report):
    output_path = tmp_path / "report.md"
    generate_markdown_report(report, output_path=str(output_path))

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content == render_markdown_report(report)


def test_markdown_report_is_well_formed_per_commonmark(report):
    """The <details> block must terminate at a blank line so nested
    markdown (headers, tables) parses correctly, not as raw HTML/plain
    text. Verified against a CommonMark/GFM-compliant parser, not
    Python-Markdown, which doesn't follow this rule the same way and
    would give a false negative here."""
    from markdown_it import MarkdownIt

    md = render_markdown_report(report)
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    html = parser.render(md)

    assert "<h3>Missing values (%)</h3>" in html
    assert "<table>" in html
