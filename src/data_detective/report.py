import json


def print_report(report: dict):
    print("\n🕵️ DATA DETECTIVE INTELLIGENCE REPORT")
    print("=" * 70)

    print(f"\n📦 Shape: {report['shape']}")

    print("\n🚨 Duplicates:")
    print(report["duplicates"])

    print("\n📉 Missing Values (%):")
    print(json.dumps(report["missing_percentage"], indent=2))

    print("\n🆔 High Cardinality Columns (possible IDs):")
    print(report["high_cardinality_columns"])

    print("\n⚠️ Constant Columns:")
    print(report["constant_columns"])

    print("\n📊 Outliers per Column:")
    print(json.dumps(report["outliers"], indent=2))

    print("\n🧠 INSIGHTS:")
    for i in report["insights"]:
        print("-", i)