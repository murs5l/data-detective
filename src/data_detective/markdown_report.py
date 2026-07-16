from __future__ import annotations

from pathlib import Path


def _kv_table(d: dict, empty_message: str = "None found.") -> str:
    if not d:
        return f"_{empty_message}_\n"
    rows = "\n".join(f"| {k} | {v} |" for k, v in d.items())
    return f"| Column | Value |\n|---|---|\n{rows}\n"


def _list(items: list, empty_message: str = "None found.") -> str:
    if not items:
        return f"_{empty_message}_\n"
    return "\n".join(f"- `{item}`" for item in items) + "\n"


def _pairs(pairs: list, empty_message: str = "None found.") -> str:
    if not pairs:
        return f"_{empty_message}_\n"
    lines = []
    for pair in pairs:
        if len(pair) == 3:
            a, b, score = pair
            lines.append(f"- `{a}` ↔ `{b}` (score: {score})")
        else:
            a, b = pair
            lines.append(f"- `{a}` ↔ `{b}`")
    return "\n".join(lines) + "\n"


def _correlation_table(matrix: dict) -> str:
    cols = list(matrix.keys())
    if len(cols) < 2:
        return "_Not enough numeric columns for a correlation matrix._\n"
    header = "| | " + " | ".join(cols) + " |\n"
    header += "|---|" + "---|" * len(cols) + "\n"
    rows = ""
    for row_key in cols:
        cells = " | ".join(f"{matrix[row_key].get(col_key, 0):.2f}" for col_key in cols)
        rows += f"| **{row_key}** | {cells} |\n"
    return header + rows


def generate_markdown_report(report: dict, output_path: str = "report.md") -> None:
    """
    Renders a CI/PR-friendly Markdown report: health score and insights lead
    (the part worth reading in a PR comment or Slack post), technical detail
    is tucked into a collapsible <details> block, which GitHub natively
    renders collapsed in PR comments and issue bodies.
    """
    Path(output_path).write_text(render_markdown_report(report), encoding="utf-8")
    print(f"📄 Markdown report generated: {output_path}")


def render_markdown_report(report: dict) -> str:
    """Same content as generate_markdown_report(), returned as a string
    instead of written to a file (used by the API, which streams it back
    as a response body rather than writing to disk)."""
    shape = report.get("shape", {})
    rows = shape.get("rows", "N/A")
    cols = shape.get("columns", "N/A")
    duplicates = report.get("duplicates", 0)
    health = report.get("health_score")

    lines = ["# 🕵️ Data Detective Report", ""]

    if health:
        lines.append(f"**Data Health Score: {health['score']}/100 ({health['grade']})**")
        lines.append("")
        breakdown = {k: v for k, v in health.get("breakdown", {}).items() if v > 0}
        if breakdown:
            lines.append("<details>")
            lines.append("<summary>Score breakdown</summary>")
            lines.append("")
            lines.append("| Category | Deduction |")
            lines.append("|---|---|")
            for category, points in sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True):
                lines.append(f"| {category.replace('_', ' ').title()} | -{points} |")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append(f"**Shape:** {rows} rows &times; {cols} columns &nbsp;|&nbsp; **Duplicate rows:** {duplicates}")
    lines.append("")

    lines.append("## Insights")
    insights = report.get("insights", [])
    if insights:
        for insight in insights:
            lines.append(f"- {insight}")
    else:
        lines.append("_No notable insights. Data looks clean. ✅_")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>Full technical report</summary>")
    lines.append("")

    lines.append("### Missing values (%)")
    lines.append(_kv_table(report.get("missing_percentage", {}), "No missing values."))

    lines.append("### Outliers (MAD)")
    lines.append(_kv_table(report.get("outliers_mad", {}), "No outliers detected."))

    lines.append("### Outliers (IQR)")
    lines.append(_kv_table(report.get("outliers_iqr", {}), "No outliers detected."))

    lines.append("### High-cardinality columns")
    lines.append(_list(report.get("high_cardinality_columns", [])))

    lines.append("### Constant columns")
    lines.append(_list(report.get("constant_columns", [])))

    lines.append("### Near-constant columns")
    lines.append(_list(report.get("near_constant_columns", [])))

    lines.append("### Possible target column")
    lines.append(_list(report.get("possible_target_columns", [])))

    lines.append("### Duplicate columns")
    lines.append(_pairs(report.get("duplicate_columns", [])))

    lines.append("### Correlated pairs")
    lines.append(_pairs(report.get("correlated_columns", [])))

    lines.append("### Correlation matrix")
    lines.append(_correlation_table(report.get("correlation_matrix", {})))

    lines.append("### Date-like columns")
    lines.append(_list(report.get("date_like_columns", [])))

    lines.append("### Mixed-type columns")
    lines.append(_list(report.get("mixed_type_columns", [])))

    lines.append("### Negative values (unexpected)")
    lines.append(_list(report.get("negative_in_nonnegative_columns", [])))

    lines.append("### Memory usage (KB)")
    lines.append(_kv_table(report.get("memory_usage_kb", {}), "No data."))

    lines.append("</details>")
    lines.append("")

    return "\n".join(lines)
