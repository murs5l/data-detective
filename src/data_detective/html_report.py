from pathlib import Path
from html import escape


def _render_kv_table(d: dict, empty_message="No data.") -> str:
    if not d:
        return f'<p class="empty">{empty_message}</p>'

    rows = "".join(
        f"<tr><td>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>"
        for k, v in d.items()
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _render_list(items: list, empty_message="None found.") -> str:
    if not items:
        return f'<p class="empty">{empty_message}</p>'

    lis = "".join(f"<li>{escape(str(item))}</li>" for item in items)
    return f"<ul>{lis}</ul>"


def _render_pairs(pairs: list, empty_message="None found.") -> str:
    """Renders list of tuples like (col_a, col_b) or (col_a, col_b, score)."""
    if not pairs:
        return f'<p class="empty">{empty_message}</p>'

    lis = []
    for pair in pairs:
        if len(pair) == 3:
            a, b, score = pair
            lis.append(f"<li><strong>{escape(str(a))}</strong> ↔ <strong>{escape(str(b))}</strong> (score: {score})</li>")
        else:
            a, b = pair
            lis.append(f"<li><strong>{escape(str(a))}</strong> ↔ <strong>{escape(str(b))}</strong></li>")

    return f"<ul>{''.join(lis)}</ul>"


def _render_nested_table(d: dict, empty_message="No data.") -> str:
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


def _render_insights(insights: list) -> str:
    if not insights:
        return '<p class="empty">No notable insights — data looks clean. ✅</p>'

    items = "".join(f'<li class="insight">{escape(item)}</li>' for item in insights)
    return f'<ul class="insights-list">{items}</ul>'


def generate_html_report(report: dict, output_path="report.html"):
    shape = report.get("shape", {})
    rows = shape.get("rows", "—")
    cols = shape.get("columns", "—")
    duplicates = report.get("duplicates", 0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Data Detective Report</title>
<style>
    :root {{
        --bg: #f5f5f7;
        --card-bg: #ffffff;
        --text: #1d1d1f;
        --muted: #6e6e73;
        --accent: #0071e3;
        --border: #e5e5e7;
        --danger: #d70015;
        --warning: #c9720b;
    }}

    * {{ box-sizing: border-box; }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        margin: 0;
        padding: 48px 24px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }}

    .container {{
        max-width: 920px;
        margin: 0 auto;
    }}

    header {{
        margin-bottom: 32px;
    }}

    header h1 {{
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 4px 0;
    }}

    header p {{
        color: var(--muted);
        margin: 0;
        font-size: 15px;
    }}

    .stat-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
    }}

    .stat-card {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }}

    .stat-card .value {{
        font-size: 28px;
        font-weight: 700;
    }}

    .stat-card .label {{
        font-size: 13px;
        color: var(--muted);
        margin-top: 4px;
    }}

    .box {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
    }}

    .box h2 {{
        font-size: 17px;
        font-weight: 600;
        margin: 0 0 14px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}

    td {{
        padding: 9px 4px;
        border-bottom: 1px solid var(--border);
    }}

    td:first-child {{
        color: var(--muted);
        width: 60%;
    }}

    td:last-child {{
        font-weight: 500;
        text-align: right;
    }}

    .nested-summary td:last-child,
    .nested td:last-child {{
        text-align: left;
    }}

    .nested {{
        width: 100%;
    }}

    .nested td {{
        padding: 4px 0;
        border-bottom: none;
    }}

    tr:last-child td {{
        border-bottom: none;
    }}

    ul {{
        margin: 0;
        padding-left: 20px;
        font-size: 14px;
    }}

    ul li {{
        margin-bottom: 6px;
    }}

    .insights-list {{
        list-style: none;
        padding-left: 0;
    }}

    .insights-list li {{
        background: #f9f9fb;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 14px;
    }}

    .empty {{
        color: var(--muted);
        font-size: 14px;
        font-style: italic;
        margin: 0;
    }}

    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }}

    @media (max-width: 640px) {{
        .grid-2 {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>
<div class="container">

    <header>
        <h1>🕵️ Data Detective Report</h1>
        <p>Automated data profiling summary</p>
    </header>

    <div class="stat-grid">
        <div class="stat-card">
            <div class="value">{rows}</div>
            <div class="label">Rows</div>
        </div>
        <div class="stat-card">
            <div class="value">{cols}</div>
            <div class="label">Columns</div>
        </div>
        <div class="stat-card">
            <div class="value">{duplicates}</div>
            <div class="label">Duplicate rows</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>📉 Missing Values (%)</h2>
            {_render_kv_table(report.get("missing_percentage", {}), "No missing values.")}
        </div>

        <div class="box">
            <h2>📊 Outliers (IQR)</h2>
            {_render_kv_table(report.get("outliers_iqr", {}), "No outliers detected.")}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>📊 Outliers (MAD)</h2>
            {_render_kv_table(report.get("outliers_mad", {}), "No outliers detected.")}
        </div>

        <div class="box">
            <h2>🧠 Distribution Shape</h2>
            {_render_nested_table(report.get("distribution_shape", {}), "No numeric columns.")}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>🆔 High Cardinality Columns</h2>
            {_render_list(report.get("high_cardinality_columns", []), "None found.")}
        </div>

        <div class="box">
            <h2>⚠️ Constant Columns</h2>
            {_render_list(report.get("constant_columns", []), "None found.")}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>🧬 Duplicate Columns</h2>
            {_render_pairs(report.get("duplicate_columns", []), "None found.")}
        </div>

        <div class="box">
            <h2>🔗 Correlated Columns</h2>
            {_render_pairs(report.get("correlated_columns", []), "None found.")}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>🧩 Mixed Type Columns</h2>
            {_render_list(report.get("mixed_type_columns", []), "None found.")}
        </div>

        <div class="box">
            <h2>➖ Negative Values</h2>
            {_render_list(report.get("negative_in_nonnegative_columns", []), "None found.")}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h2>💾 Memory Usage (KB)</h2>
            {_render_kv_table(report.get("memory_usage_kb", {}), "No data.")}
        </div>

        <div class="box">
            <h2>📝 Text Column Stats</h2>
            {_render_nested_table(report.get("text_column_stats", {}), "No text columns.")}
        </div>
    </div>

    <div class="box">
        <h2>📅 Date-like Columns</h2>
        {_render_list(report.get("date_like_columns", []), "None found.")}
    </div>

    <div class="box">
        <h2>🧠 Insights</h2>
        {_render_insights(report.get("insights", []))}
    </div>

</div>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"📄 HTML report generated: {output_path}")