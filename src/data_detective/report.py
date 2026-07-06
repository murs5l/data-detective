import json


def pretty(x):
    if isinstance(x, (dict, list)):
        return json.dumps(x, indent=2)
    return str(x)


def print_report(report: dict):
    print("\n🕵️ DATA DETECTIVE INTELLIGENCE REPORT")
    print("=" * 70)

    print(f"\n📦 Shape: {pretty(report.get('shape', {}))}")

    print("\n🚨 Duplicates:")
    print(pretty(report.get("duplicates", 0)))

    print("\n📉 Missing Values:")
    print(pretty(report.get("missing_values", {})))

    print("\n🆔 High Cardinality Columns (possible IDs):")
    print(pretty(report.get("high_cardinality_columns", [])))

    print("\n⚠️ Constant Columns:")
    print(pretty(report.get("constant_columns", [])))

    print("\n📊 Outliers per Column:")
    print(pretty(report.get("outliers", {})))

    print("\n🧠 INSIGHTS:")
    for i in report.get("insights", []):
        print("-", i)