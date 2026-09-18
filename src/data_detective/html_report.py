from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Callable, Optional


def _render_kv_table(d: dict[str, Any], empty_message: str = "No data.") -> str:
    if not d:
        return f'<p class="empty">{empty_message}</p>'

    rows = "".join(
        f"<tr><td>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>"
        for k, v in d.items()
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _render_list(items: list[Any], empty_message: str = "None found.") -> str:
    if not items:
        return f'<p class="empty">{empty_message}</p>'

    lis = "".join(f"<li>{escape(str(item))}</li>" for item in items)
    return f"<ul>{lis}</ul>"


def _render_pairs(pairs: list[tuple], empty_message: str = "None found.") -> str:
    """Renders list of tuples like (col_a, col_b) or (col_a, col_b, score)."""
    if not pairs:
        return f'<p class="empty">{empty_message}</p>'

    lis = []
    for pair in pairs:
        if len(pair) == 3:
            a, b, score = pair
            lis.append(
                f"<li><strong>{escape(str(a))}</strong> ↔ <strong>{escape(str(b))}</strong> "
                f"(score: {score})</li>"
            )
        else:
            a, b = pair
            lis.append(f"<li><strong>{escape(str(a))}</strong> ↔ <strong>{escape(str(b))}</strong></li>")

    return f"<ul>{''.join(lis)}</ul>"


def _render_nested_table(d: dict[str, Any], empty_message: str = "No data.") -> str:
    if not d:
        return f'<p class="empty">{empty_message}</p>'

    rows = []
    for outer_key, inner_value in d.items():
        if isinstance(inner_value, dict):
            nested_rows = "".join(
                f"<tr><td>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>"
                for k, v in inner_value.items()
            )
            nested_html = f'<table class="nested"><tbody>{nested_rows}</tbody></table>'
        else:
            nested_html = escape(str(inner_value))
        rows.append(f"<tr><td>{escape(str(outer_key))}</td><td>{nested_html}</td></tr>")

    return f'<table class="nested-summary"><tbody>{"".join(rows)}</tbody></table>'


def _render_insights(insights: list[str]) -> str:
    if not insights:
        return '<p class="empty">No notable insights. Data looks clean. ✅</p>'

    items = "".join(f'<li class="insight">{escape(item)}</li>' for item in insights)
    return f'<ul class="insights-list">{items}</ul>'


_HEALTH_GRADE_CLASS = {"Fair": "grade-fair", "Poor": "grade-poor", "Critical": "grade-poor"}

_HEALTH_BREAKDOWN_LABELS = {
    "missing_values": "Missing values",
    "duplicate_rows": "Duplicate rows",
    "outliers": "Outliers",
    "duplicate_columns": "Duplicate columns",
    "constant_columns": "Constant columns",
    "mixed_type_columns": "Mixed-type columns",
    "negative_values": "Unexpected negatives",
    "skewed_distributions": "Skewed distributions",
    "correlated_columns": "Correlated columns",
    "near_constant_columns": "Near-constant columns",
    "date_like_columns": "Date-like columns",
}


def _render_informational_notice(health: dict[str, Any]) -> str:
    informational = health.get("informational_categories", [])
    if not informational:
        return ""
    labels = ", ".join(_HEALTH_BREAKDOWN_LABELS.get(col, col).lower() for col in informational)
    return f'<p class="health-score-informational">Tracked but not scored: {escape(labels)}</p>'


def _render_hero(report: dict[str, Any]) -> str:
    """
    The health score is the visual hero: score, grade, and the top-line
    counts a reader needs before digging into anything else. Per-category
    deduction detail lives in the "What needs attention" section below,
    not duplicated here as a second breakdown list.
    """
    health = report.get("health_score", {})
    if not health:
        return ""

    shape = report.get("shape", {})
    grade_class = _HEALTH_GRADE_CLASS.get(health.get("grade", ""), "")
    issues_detected = sum(1 for points in health.get("breakdown", {}).values() if points > 0)

    return f"""
    <div class="box hero-card">
        <div class="hero-top">
            <div class="health-score-badge {grade_class}">
                <div class="health-score-number">{health.get('score', 'N/A')}</div>
                <div class="health-score-denom">/ 100</div>
            </div>
            <div class="hero-heading">
                <h2>🏥 Data Health Score</h2>
                <span class="health-score-grade {grade_class}">{escape(str(health.get('grade', '')))}</span>
                {_render_informational_notice(health)}
            </div>
        </div>
        <div class="hero-stats">
            <div class="hero-stat">
                <div class="hero-stat-value">{issues_detected}</div>
                <div class="hero-stat-label">Issues detected</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-value">{shape.get('rows', 'N/A')}</div>
                <div class="hero-stat-label">Rows</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-value">{shape.get('columns', 'N/A')}</div>
                <div class="hero-stat-label">Columns</div>
            </div>
        </div>
    </div>"""


def _format_columns(cols: list[str], limit: int = 3) -> str:
    if not cols:
        return ""
    shown = ", ".join(cols[:limit])
    if len(cols) > limit:
        shown += f", +{len(cols) - limit} more"
    return shown


def _worst_by_value(d: dict[str, float]) -> Optional[tuple[str, float]]:
    if not d:
        return None
    col = max(d, key=lambda k: d[k])
    return col, d[col]


def _attention_row_missing_values(report: dict[str, Any]) -> tuple[str, str]:
    worst = _worst_by_value(report.get("missing_percentage", {}))
    if not worst:
        return "", ""
    col, pct = worst
    return col, f"{pct}%"


def _attention_row_duplicate_rows(report: dict[str, Any]) -> tuple[str, str]:
    return "", str(report.get("duplicate_rows", 0))


def _attention_row_outliers(report: dict[str, Any]) -> tuple[str, str]:
    outliers = report.get("outliers_mad") or report.get("outliers_iqr") or {}
    worst = _worst_by_value(outliers)
    if not worst:
        return "", ""
    col, count = worst
    return col, str(int(count))


def _attention_row_duplicate_columns(report: dict[str, Any]) -> tuple[str, str]:
    pairs = report.get("duplicate_columns", [])
    if not pairs:
        return "", "0"
    a, b = pairs[0][0], pairs[0][1]
    context = f"{a} ↔ {b}" if len(pairs) == 1 else f"{a} ↔ {b}, +{len(pairs) - 1} more"
    return context, str(len(pairs))


def _attention_row_correlated_columns(report: dict[str, Any]) -> tuple[str, str]:
    pairs = report.get("correlated_columns", [])
    if not pairs:
        return "", "0"
    a, b, score = pairs[0]
    context = f"{a} ↔ {b}" if len(pairs) == 1 else f"{a} ↔ {b}, +{len(pairs) - 1} more"
    return context, str(score)


def _attention_row_skewed_distributions(report: dict[str, Any]) -> tuple[str, str]:
    shapes = report.get("distribution_shape", {})
    if not shapes:
        return "", ""
    col = max(shapes, key=lambda c: abs(shapes[c]["skewness"]))
    return col, f"skew={shapes[col]['skewness']}"


def _make_column_list_attention_row(report_key: str) -> Callable[[dict[str, Any]], tuple[str, str]]:
    def row(report: dict[str, Any]) -> tuple[str, str]:
        cols = report.get(report_key, [])
        return _format_columns(cols), str(len(cols))

    return row


# One builder per scoreable health-score category (see
# DataProfiler.HEALTH_SCORE_MAX_DEDUCTIONS), producing (where, value) for
# the "What needs attention" table from data the report already contains.
# No new detectors or statistics: each builder only selects/formats fields
# run_full_profile() already computed.
_ATTENTION_ROW_BUILDERS: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "missing_values": _attention_row_missing_values,
    "duplicate_rows": _attention_row_duplicate_rows,
    "outliers": _attention_row_outliers,
    "duplicate_columns": _attention_row_duplicate_columns,
    "constant_columns": _make_column_list_attention_row("constant_columns"),
    "mixed_type_columns": _make_column_list_attention_row("mixed_type_columns"),
    "negative_values": _make_column_list_attention_row("negative_in_nonnegative_columns"),
    "skewed_distributions": _attention_row_skewed_distributions,
    "correlated_columns": _attention_row_correlated_columns,
    "near_constant_columns": _make_column_list_attention_row("near_constant_columns"),
    "date_like_columns": _make_column_list_attention_row("date_like_columns"),
}


def _render_attention_section(report: dict[str, Any]) -> str:
    breakdown = report.get("health_score", {}).get("breakdown", {})
    deductions = sorted(
        ((category, points) for category, points in breakdown.items() if points > 0),
        key=lambda pair: pair[1],
        reverse=True,
    )

    if not deductions:
        return '<p class="empty">No major issues detected. ✅</p>'

    rows_html = []
    for category, points in deductions:
        builder = _ATTENTION_ROW_BUILDERS.get(category)
        where, value = builder(report) if builder else ("", "")
        label = _HEALTH_BREAKDOWN_LABELS.get(category, category)
        rows_html.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{escape(where)}</td>"
            f"<td>{escape(value)}</td>"
            "</tr>"
        )

    return (
        '<table class="attention-table"><thead><tr><th>Issue</th><th>Where</th><th>Value</th></tr></thead>'
        f"<tbody>{''.join(rows_html)}</tbody></table>"
    )


def _render_missing_values_summary(report: dict[str, Any], top_n: int = 8) -> str:
    missing_pct = {col: pct for col, pct in report.get("missing_percentage", {}).items() if pct > 0}
    if not missing_pct:
        return '<p class="empty">No missing values.</p>'

    top = sorted(missing_pct.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    rows = "".join(
        '<div class="missing-bar-row">'
        f'<span class="missing-bar-label">{escape(col)}</span>'
        f'<div class="missing-bar-track"><div class="missing-bar-fill" style="width:{min(pct, 100):.1f}%"></div></div>'
        f'<span class="missing-bar-value">{pct}%</span>'
        "</div>"
        for col, pct in top
    )
    return f'<div class="missing-bar-list">{rows}</div>'


def _render_dataset_structure(report: dict[str, Any]) -> str:
    shape = report.get("shape", {})
    rows, cols = shape.get("rows", 0), shape.get("columns", 0)
    # outliers_iqr covers exactly the numeric columns run_full_profile()
    # considers numeric (detect_outliers() iterates self._numeric_df.columns
    # unconditionally), so its key count is the numeric-column count without
    # re-deriving it from dtype strings.
    numeric_columns = len(report.get("outliers_iqr", {}))
    other_columns = max(cols - numeric_columns, 0)
    total_missing_cells = sum(report.get("missing_values", {}).values())
    total_cells = rows * cols
    missing_cell_pct = round(total_missing_cells / total_cells * 100, 2) if total_cells else 0.0

    facts = {
        "Rows": rows,
        "Columns": cols,
        "Numeric columns": numeric_columns,
        "Text / other columns": other_columns,
        "Duplicate rows": report.get("duplicate_rows", 0),
        "Missing cells": f"{total_missing_cells} ({missing_cell_pct}%)",
    }
    return _render_kv_table(facts)


def _render_overview_grid(report: dict[str, Any]) -> str:
    return f"""
    <div class="box">
        <div class="grid-2">
            <div>
                <h3 class="panel-title">Missing values</h3>
                {_render_missing_values_summary(report)}
            </div>
            <div>
                <h3 class="panel-title">Dataset structure</h3>
                {_render_dataset_structure(report)}
            </div>
        </div>
    </div>"""


def _color_for_correlation(value: float) -> str:
    """Blue for positive correlation, pink/red for negative, scaled by strength."""
    v = max(-1.0, min(1.0, value))
    if v >= 0:
        intensity = round(255 - v * 140)
        return f"rgb({intensity - 60}, {intensity - 20}, 255)"
    intensity = round(255 + v * 140)
    return f"rgb(255, {intensity - 60}, {intensity - 20})"


def _render_correlation_heatmap(
    matrix: dict[str, dict[str, float]],
    partial_analysis_notices: list[str] | None = None,
    empty_message: str = "Not enough numeric columns for a heatmap.",
) -> str:
    cols = list(matrix.keys())
    if len(cols) < 2:
        if partial_analysis_notices:
            notices_html = "".join(
                f'<p class="partial-analysis-notice">{escape(notice)}</p>' for notice in partial_analysis_notices
            )
            return notices_html
        return f'<p class="empty">{empty_message}</p>'

    header_cells = "".join(f"<th>{escape(str(c))}</th>" for c in cols)
    body_rows = []
    for row_key in cols:
        cells = []
        for col_key in cols:
            value = matrix[row_key].get(col_key, 0)
            color = _color_for_correlation(value)
            cells.append(f'<td><div class="heatmap-cell" style="background:{color}">{value:.2f}</div></td>')
        body_rows.append(f"<tr><th>{escape(str(row_key))}</th>{''.join(cells)}</tr>")

    return (
        '<div class="heatmap-wrap"><table class="heatmap-table"><thead>'
        f"<tr><th></th>{header_cells}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _render_explorer_histogram(hist: dict[str, Any], empty_message: str = "No histogram data for this column.") -> str:
    if not hist:
        return f'<p class="empty">{empty_message}</p>'

    bin_edges = hist.get("bin_edges", [])
    counts = hist.get("counts", [])
    max_count = max(counts) if counts else 1

    bars = []
    for i, c in enumerate(counts):
        height = max((c / max_count) * 100, 2)
        edge = bin_edges[i] if i < len(bin_edges) else ""
        next_edge = bin_edges[i + 1] if i + 1 < len(bin_edges) else ""
        title = escape(f"{edge} to {next_edge}: {c} rows")
        bars.append(
            f'<div class="explorer-hist-bar-wrap" title="{title}">'
            f'<div class="explorer-hist-count">{c}</div>'
            f'<div class="hist-bar" style="height:{height:.1f}%"></div>'
            f'<div class="explorer-hist-edge">{escape(str(edge))}</div>'
            "</div>"
        )

    return f'<div class="explorer-hist-bars">{"".join(bars)}</div>'


def _render_explorer_stats(col: str, box: dict[str, Any], report: dict[str, Any]) -> str:
    if not box:
        return ""

    shape = report.get("distribution_shape", {}).get(col)
    outliers_mad = report.get("outliers_mad", {}).get(col)
    outliers_iqr = report.get("outliers_iqr", {}).get(col)
    missing_pct = report.get("missing_percentage", {}).get(col)

    stats = [
        ("Min", box["min"]),
        ("Q1", box["q1"]),
        ("Median", box["median"]),
        ("Q3", box["q3"]),
        ("Max", box["max"]),
        ("Outliers beyond whiskers", len(box["outliers"])),
    ]
    if outliers_mad is not None:
        stats.append(("Outliers (MAD)", outliers_mad))
    if outliers_iqr is not None:
        stats.append(("Outliers (IQR)", outliers_iqr))
    if shape:
        stats.append(("Skewness", shape["skewness"]))
        stats.append(("Kurtosis", shape["kurtosis"]))
    if missing_pct is not None:
        stats.append(("Missing", f"{missing_pct}%"))

    chips = "".join(
        f'<div class="stat-chip"><span class="stat-chip-value">{escape(str(value))}</span>'
        f'<span class="stat-chip-label">{escape(str(label))}</span></div>'
        for label, value in stats
    )
    return f'<div class="explorer-stats">{chips}</div>'


def _render_column_explorer(report: dict[str, Any]) -> str:
    """
    Interactive per-column drill-down: a dropdown switches between hidden
    panels (one per column) via a tiny inline script, so this works in a
    standalone HTML file with no server. High-cardinality (ID-like) and
    constant columns are excluded since a chart of them isn't meaningful.
    """
    histograms = report.get("histogram_data", {})
    boxplots = report.get("boxplot_stats", {})
    excluded = set(report.get("high_cardinality_columns", [])) | set(report.get("constant_columns", []))

    columns = []
    for col in list(histograms.keys()) + list(boxplots.keys()):
        if col not in excluded and col not in columns:
            columns.append(col)

    note = (
        '<p class="explorer-note">ID-like and constant columns are left out here since a chart of '
        "them isn't meaningful. See the full technical report below for those.</p>"
    )

    if not columns:
        if not histograms and not boxplots:
            return note + '<p class="empty">No numeric columns to chart.</p>'
        return note + (
            '<p class="empty">No columns suitable for detailed charting: the remaining numeric '
            "columns look like IDs or are constant.</p>"
        )

    options = "".join(f'<option value="{escape(col)}">{escape(col)}</option>' for col in columns)

    panels = []
    for i, col in enumerate(columns):
        hidden_attr = "" if i == 0 else " hidden"
        box = boxplots.get(col)
        boxplot_html = _boxplot_svg(box) if box else '<p class="empty">No boxplot data.</p>'
        panels.append(
            f'<div class="explorer-panel"{hidden_attr} data-column="{escape(col)}">'
            '<div class="grid-2">'
            f'<div class="explorer-block"><h4>Histogram</h4>{_render_explorer_histogram(histograms.get(col))}</div>'
            f'<div class="explorer-block"><h4>Boxplot</h4>{boxplot_html}</div>'
            "</div>"
            f"{_render_explorer_stats(col, box, report)}"
            "</div>"
        )

    controls = (
        '<div class="explorer-controls"><label for="column-select">Column</label>'
        f'<select id="column-select" onchange="ddShowColumn(this.value)">{options}</select></div>'
    )

    script = (
        "<script>\n"
        "function ddShowColumn(col) {\n"
        "    document.querySelectorAll('.explorer-panel').forEach(function (el) {\n"
        "        el.hidden = el.getAttribute('data-column') !== col;\n"
        "    });\n"
        "}\n"
        "</script>"
    )

    return note + controls + f'<div id="explorer-blocks">{"".join(panels)}</div>' + script


def _boxplot_svg(box: dict[str, Any]) -> str:
    width, height, padding = 300, 46, 14
    values = [box["min"], box["max"], box["whisker_low"], box["whisker_high"], *box["outliers"]]
    domain_min, domain_max = min(values), max(values)
    span = (domain_max - domain_min) or 1

    def scale(v):
        return padding + ((v - domain_min) / span) * (width - 2 * padding)

    def svg_line(css_class, x1, y1, x2, y2):
        return f'<line class="{css_class}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" />'

    mid_y = height / 2
    box_top = mid_y - 13
    box_height = 26
    whisker_low_x = scale(box["whisker_low"])
    whisker_high_x = scale(box["whisker_high"])

    whisker_line = svg_line("box-whisker", whisker_low_x, mid_y, whisker_high_x, mid_y)
    cap_low = svg_line("box-whisker", whisker_low_x, mid_y - 6, whisker_low_x, mid_y + 6)
    cap_high = svg_line("box-whisker", whisker_high_x, mid_y - 6, whisker_high_x, mid_y + 6)
    box_x = scale(box["q1"])
    box_width = max(scale(box["q3"]) - scale(box["q1"]), 1)
    rect = f'<rect class="box-rect" x="{box_x}" y="{box_top}" width="{box_width}" height="{box_height}" rx="3" />'
    median_x = scale(box["median"])
    median = svg_line("box-median", median_x, box_top, median_x, box_top + box_height)
    outliers = "".join(
        f'<circle class="box-outlier" cx="{scale(v)}" cy="{mid_y}" r="3" />' for v in box["outliers"]
    )

    return (
        f'<svg class="box-plot-svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f"{whisker_line}{cap_low}{cap_high}{rect}{median}{outliers}</svg>"
    )


# (title, report key, render helper, empty message) for each section of the
# collapsed technical report. Declarative so adding a detector's output here
# is a one-line addition, not another copy-pasted <div class="tech-box">.
_TECH_SECTIONS = (
    ("Column types", "column_types", _render_kv_table, "No data."),
    ("Missing values (%)", "missing_percentage", _render_kv_table, "No missing values."),
    ("Outliers (IQR)", "outliers_iqr", _render_kv_table, "No outliers detected."),
    ("Outliers (MAD)", "outliers_mad", _render_kv_table, "No outliers detected."),
    ("Distribution shape", "distribution_shape", _render_nested_table, "No numeric columns."),
    ("High-cardinality columns", "high_cardinality_columns", _render_list, "None found."),
    ("Constant columns", "constant_columns", _render_list, "None found."),
    ("Near-constant columns", "near_constant_columns", _render_list, "None found."),
    ("Possible target column", "possible_target_columns", _render_list, "None found."),
    ("Duplicate columns", "duplicate_columns", _render_pairs, "None found."),
    ("Correlated pairs", "correlated_columns", _render_pairs, "None found."),
    ("Mixed-type columns", "mixed_type_columns", _render_list, "None found."),
    ("Negative values (unexpected)", "negative_in_nonnegative_columns", _render_list, "None found."),
    ("Memory usage (KB)", "memory_usage_kb", _render_kv_table, "No data."),
    ("Text column stats", "text_column_stats", _render_nested_table, "No text columns."),
    ("Date-like columns", "date_like_columns", _render_list, "None found."),
)


def _render_technical_report(report: dict[str, Any]) -> str:
    # {} is a safe empty-collection default for every renderer here: each
    # one only ever checks `if not x` for its "nothing to show" branch, so
    # a missing key renders identically regardless of the section's real
    # value type (list of columns vs. dict of column -> stat).
    boxes = "".join(
        f'<div class="tech-box"><h3>{title}</h3>{render(report.get(key, {}), empty)}</div>'
        for title, key, render, empty in _TECH_SECTIONS
    )
    return f"""
    <details class="box details-card">
        <summary>🔬 Full technical report</summary>

        <div class="tech-grid">{boxes}</div>
    </details>"""


_STYLES = """
    :root {
        --bg: #f5f5f7;
        --card-bg: #ffffff;
        --text: #1d1d1f;
        --muted: #6e6e73;
        --accent: #0071e3;
        --border: #e5e5e7;
        --danger: #d70015;
        --warning: #c9720b;
        --success: #1a8a3f;
        --success-bg: #e8f7ec;
        --warning-bg: #fff6ea;
        --danger-bg: #fdecec;
    }

    * { box-sizing: border-box; }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        margin: 0;
        padding: 48px 24px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }

    .container {
        max-width: 920px;
        margin: 0 auto;
    }

    header {
        margin-bottom: 32px;
    }

    .header-row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
    }

    header h1 {
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 4px 0;
    }

    header p {
        color: var(--muted);
        margin: 0;
        font-size: 15px;
    }

    .header-timestamp {
        font-size: 13px;
        color: var(--muted);
    }

    .box {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        /* Grid items default to min-width: auto, which lets wide content
           (e.g. the correlation heatmap table) force the whole grid, and
           the page, to overflow horizontally instead of scrolling here. */
        min-width: 0;
    }

    .box h2 {
        font-size: 17px;
        font-weight: 600;
        margin: 0 0 14px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .panel-title {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted);
        margin: 0 0 12px 0;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }

    td {
        padding: 9px 4px;
        border-bottom: 1px solid var(--border);
    }

    td:first-child {
        color: var(--muted);
        width: 60%;
    }

    td:last-child {
        font-weight: 500;
        text-align: right;
    }

    .nested-summary td:last-child,
    .nested td:last-child,
    .attention-table td:last-child {
        text-align: left;
    }

    .nested {
        width: 100%;
    }

    .nested td {
        padding: 4px 0;
        border-bottom: none;
    }

    tr:last-child td {
        border-bottom: none;
    }

    ul {
        margin: 0;
        padding-left: 20px;
        font-size: 14px;
    }

    ul li {
        margin-bottom: 6px;
    }

    .hero-card {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .hero-top {
        display: flex;
        align-items: center;
        gap: 24px;
    }

    .health-score-badge {
        flex-shrink: 0;
        width: 96px;
        height: 96px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: var(--success-bg);
        border: 3px solid var(--success);
    }

    .health-score-number {
        font-size: 30px;
        font-weight: 700;
        line-height: 1;
        color: var(--success);
    }

    .health-score-denom {
        font-size: 11px;
        color: var(--muted);
        margin-top: 2px;
    }

    .health-score-badge.grade-fair {
        background: var(--warning-bg);
        border-color: var(--warning);
    }
    .health-score-badge.grade-fair .health-score-number {
        color: var(--warning);
    }

    .health-score-badge.grade-poor {
        background: var(--danger-bg);
        border-color: var(--danger);
    }
    .health-score-badge.grade-poor .health-score-number {
        color: var(--danger);
    }

    .hero-heading {
        flex: 1;
        min-width: 0;
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }

    .hero-heading h2 {
        margin: 0;
    }

    .health-score-grade {
        font-size: 13px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 999px;
        background: var(--success-bg);
        color: var(--success);
    }

    .health-score-grade.grade-fair {
        background: var(--warning-bg);
        color: var(--warning);
    }

    .health-score-grade.grade-poor {
        background: var(--danger-bg);
        color: var(--danger);
    }

    .health-score-informational {
        flex-basis: 100%;
        font-size: 12px;
        color: var(--muted);
        font-style: italic;
        margin: 4px 0 0 0;
    }

    .hero-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 16px;
        padding-top: 4px;
        border-top: 1px solid var(--border);
    }

    .hero-stat {
        text-align: center;
    }

    .hero-stat-value {
        font-size: 24px;
        font-weight: 700;
    }

    .hero-stat-label {
        font-size: 12px;
        color: var(--muted);
        margin-top: 2px;
    }

    .attention-table th {
        text-align: left;
        font-size: 12px;
        color: var(--muted);
        font-weight: 500;
        padding: 0 4px 8px 4px;
    }

    .partial-analysis-notice {
        font-size: 13px;
        color: var(--warning);
        background: var(--warning-bg);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 0;
    }

    .insights-list {
        list-style: none;
        padding-left: 0;
    }

    .insights-list li {
        background: #f9f9fb;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 14px;
    }

    .empty {
        color: var(--muted);
        font-size: 14px;
        font-style: italic;
        margin: 0;
    }

    .grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }

    @media (max-width: 640px) {
        .grid-2 { grid-template-columns: 1fr; }
    }

    .missing-bar-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .missing-bar-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 2fr auto;
        align-items: center;
        gap: 10px;
        font-size: 13px;
    }

    .missing-bar-label {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: var(--muted);
    }

    .missing-bar-track {
        background: var(--bg);
        border-radius: 999px;
        height: 8px;
        overflow: hidden;
    }

    .missing-bar-fill {
        background: var(--warning);
        height: 100%;
        border-radius: 999px;
    }

    .missing-bar-value {
        font-weight: 600;
        font-size: 12px;
        text-align: right;
    }

    .heatmap-wrap {
        overflow-x: auto;
    }

    .heatmap-table {
        border-collapse: collapse;
        font-size: 12px;
    }

    .heatmap-table th,
    .heatmap-table td {
        padding: 6px 8px;
        text-align: center;
        white-space: nowrap;
    }

    .heatmap-table th {
        color: var(--muted);
        font-weight: 500;
    }

    .heatmap-cell {
        border-radius: 6px;
        font-weight: 600;
        color: #fff;
        min-width: 46px;
        padding: 4px 0;
    }

    .explorer-note {
        font-size: 12px;
        color: var(--muted);
        margin: 0 0 16px 0;
    }

    .explorer-controls {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }

    .explorer-controls label {
        font-size: 13px;
        color: var(--muted);
    }

    .explorer-controls select {
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        background: var(--card-bg);
        color: var(--text);
    }

    .explorer-block h4 {
        margin: 0 0 10px 0;
        font-size: 13px;
        font-weight: 600;
        color: var(--muted);
    }

    .explorer-hist-bars {
        display: flex;
        align-items: flex-end;
        gap: 4px;
        height: 110px;
    }

    .explorer-hist-bar-wrap {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        height: 100%;
        min-width: 0;
    }

    .explorer-hist-count {
        font-size: 11px;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 2px;
    }

    .hist-bar {
        width: 100%;
        background: var(--accent);
        border-radius: 2px 2px 0 0;
        min-height: 2px;
    }

    .explorer-hist-edge {
        font-size: 10px;
        color: var(--muted);
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }

    .explorer-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--border);
    }

    .stat-chip {
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 12px;
        text-align: center;
        min-width: 76px;
    }

    .stat-chip-value {
        display: block;
        font-size: 15px;
        font-weight: 700;
    }

    .stat-chip-label {
        display: block;
        font-size: 11px;
        color: var(--muted);
        margin-top: 2px;
    }

    .box-plot-svg {
        width: 100%;
        height: 46px;
        display: block;
    }

    .box-whisker {
        stroke: var(--muted);
        stroke-width: 1.5;
    }

    .box-rect {
        fill: #f0f6ff;
        stroke: var(--accent);
        stroke-width: 1.5;
    }

    .box-median {
        stroke: var(--accent);
        stroke-width: 2;
    }

    .box-outlier {
        fill: var(--danger);
        opacity: 0.7;
    }

    .details-card summary {
        cursor: pointer;
        font-weight: 600;
        font-size: 17px;
        list-style: none;
    }

    .details-card summary::-webkit-details-marker {
        display: none;
    }

    .details-card[open] summary {
        margin-bottom: 16px;
    }

    .tech-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 18px;
    }

    .tech-box h3 {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted);
        margin: 0 0 8px 0;
    }
"""


def generate_html_report(report: dict[str, Any], output_path: str | Path = "report.html") -> Path:
    """
    Renders the canonical report dict (DataProfiler.run_full_profile()'s
    output) as a standalone, dependency-free HTML file and returns the
    path written to. Purely a presentation layer: every number here comes
    from a key already in `report`, nothing is recomputed.

    Callers decide what to print about the result; this function only
    writes the file.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Data Detective Report</title>
<style>{_STYLES}</style>
</head>
<body>
<div class="container">

    <header>
        <div class="header-row">
            <h1>🕵️ Data Detective</h1>
            <span class="header-timestamp">Generated {generated_at}</span>
        </div>
        <p>Dataset quality overview</p>
    </header>

    {_render_hero(report)}

    <div class="box">
        <h2>🚨 What needs attention</h2>
        {_render_attention_section(report)}
    </div>

    {_render_overview_grid(report)}

    <div class="box">
        <h2>🧠 Insights</h2>
        {_render_insights(report.get("insights", []))}
    </div>

    <div class="box">
        <h2>📊 Column Explorer</h2>
        {_render_column_explorer(report)}
    </div>

    <div class="box">
        <h2>🔗 Correlation Heatmap</h2>
        {_render_correlation_heatmap(report.get("correlation_matrix", {}), report.get("partial_analysis", []))}
    </div>

    {_render_technical_report(report)}

</div>
</body>
</html>"""

    path = Path(output_path)
    path.write_text(html, encoding="utf-8")
    return path
