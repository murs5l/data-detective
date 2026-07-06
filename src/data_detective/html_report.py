from pathlib import Path
import json


def generate_html_report(report: dict, output_path="report.html"):
    html = f"""
    <html>
    <head>
        <title>Data Detective Report</title>
        <style>
            body {{
                font-family: Arial;
                margin: 40px;
                background: #f7f7f7;
            }}
            h1 {{
                color: #222;
            }}
            .box {{
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}
            pre {{
                background: #eee;
                padding: 10px;
                border-radius: 6px;
            }}
        </style>
    </head>
    <body>

    <h1>🕵️ Data Detective Report</h1>

    <div class="box">
        <h2>📦 Shape</h2>
        <pre>{report.get("shape")}</pre>
    </div>

    <div class="box">
        <h2>🚨 Duplicates</h2>
        <pre>{report.get("duplicates")}</pre>
    </div>

    <div class="box">
        <h2>📉 Missing Values</h2>
        <pre>{json.dumps(report.get("missing_values"), indent=2)}</pre>
    </div>

    <div class="box">
        <h2>🆔 High Cardinality Columns</h2>
        <pre>{report.get("high_cardinality")}</pre>
    </div>

    <div class="box">
        <h2>⚠️ Constant Columns</h2>
        <pre>{report.get("constant_columns")}</pre>
    </div>

    <div class="box">
        <h2>📊 Outliers</h2>
        <pre>{json.dumps(report.get("outliers"), indent=2)}</pre>
    </div>

    <div class="box">
        <h2>🧠 Insights</h2>
        <pre>{report.get("insights")}</pre>
    </div>

    </body>
    </html>
    """

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"📄 HTML report generated: {output_path}")