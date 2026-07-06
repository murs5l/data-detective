import sys
import json
import argparse

from data_detective.html_report import generate_html_report
from data_detective.loader import load_csv
from data_detective.profiler import DataProfiler
from data_detective.report import print_report


# -----------------------------
# COMMAND HANDLER
# -----------------------------
def run_analyze(args):
    print("🔥 Data Detective starting...\n")

    df = load_csv(args.file)
    profiler = DataProfiler(df)
    report = profiler.run_full_profile()

    if args.html:
        generate_html_report(report)
        return

    if args.json:
        print(json.dumps(report, indent=2))
        return

    if not args.json and not args.html:
        print_report(report)

    return 0


# -----------------------------
# CLI SETUP
# -----------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="data-detective",
        description="🕵️ Data Detective - Smart Data Profiling Tool"
    )

    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a CSV file"
    )

    analyze_parser.add_argument("file", help="Path to CSV file")
    analyze_parser.add_argument("--json", action="store_true", help="Output JSON report")
    analyze_parser.add_argument("--html", action="store_true", help="Generate HTML report")

    analyze_parser.set_defaults(func=run_analyze)

    return parser


# -----------------------------
# MAIN ENTRY POINT
# -----------------------------
def main():
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


# REQUIRED ENTRY POINT
if __name__ == "__main__":
    sys.exit(main())