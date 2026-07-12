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

    print("\n📊 Outliers (IQR):")
    print(pretty(report.get("outliers_iqr", {})))

    print("\n📊 Outliers (MAD):")
    print(pretty(report.get("outliers_mad", {})))

    print("\n🧬 Duplicate Columns:")
    print(pretty(report.get("duplicate_columns", [])))

    print("\n🔗 Correlated Columns:")
    print(pretty(report.get("correlated_columns", [])))

    print("\n📅 Date-like Columns:")
    print(pretty(report.get("date_like_columns", [])))

    print("\n🧩 Mixed Type Columns:")
    print(pretty(report.get("mixed_type_columns", [])))

    print("\n💾 Memory Usage (KB):")
    print(pretty(report.get("memory_usage_kb", {})))

    print("\n➖ Negative Values in Nonnegative Columns:")
    print(pretty(report.get("negative_in_nonnegative_columns", [])))

    print("\n📐 Distribution Shape:")
    print(pretty(report.get("distribution_shape", {})))

    print("\n🧠 INSIGHTS:")
    for i in report.get("insights", []):
        print("-", i)
