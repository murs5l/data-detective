import argparse
import json
import sys
from pathlib import Path

from data_detective.exceptions import DataLoadError, EmptyDataError
from data_detective.html_report import generate_html_report
from data_detective.loader import load_csv
from data_detective.profiler import DataProfiler
from data_detective.report import print_report


# -----------------------------
# COMMAND HANDLER
# -----------------------------
def run_analyze(args):
    if not args.quiet:
        print("🔥 Data Detective starting...\n")

    df = load_csv(args.file)
    profiler = DataProfiler(df)
    report = profiler.run_full_profile(outlier_method=args.outlier_method)

    emit_html = args.html or bool(args.output_html)
    emit_json = args.json or bool(args.output_json)

    if emit_html:
        output_html_path = args.output_html or "report.html"
        generate_html_report(report, output_path=output_html_path)

    if emit_json:
        payload = json.dumps(report, indent=2)
        if args.output_json:
            Path(args.output_json).write_text(payload + "\n", encoding="utf-8")
        elif args.json:
            print(payload)

    if emit_html or emit_json:
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
    analyze_parser.add_argument("--output-json", help="Write JSON report to the given file path")
    analyze_parser.add_argument("--output-html", help="Write HTML report to the given file path")
    analyze_parser.add_argument(
        "--outlier-method",
        choices=["iqr", "mad"],
        default="mad",
        help="Outlier detection method used for insights (default: mad)",
    )
    analyze_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error progress messages",
    )

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

    try:
        return args.func(args)
    except EmptyDataError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except DataLoadError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


# REQUIRED ENTRY POINT
if __name__ == "__main__":
    sys.exit(main())
