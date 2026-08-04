import json
from pathlib import Path

import pytest

from data_detective.cli import build_parser, main


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")
    return csv_path


def _run(args_list):
    parser = build_parser()
    args = parser.parse_args(args_list)
    return args.func(args)


def test_analyze_default_prints_report(sample_csv, capsys):
    exit_code = _run(["analyze", str(sample_csv)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "INSIGHTS" in out
    assert "Tracked but not scored" in out


def test_analyze_json_flag_prints_valid_json(sample_csv, capsys):
    _run(["analyze", str(sample_csv), "--json", "--quiet"])

    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["shape"] == {"rows": 3, "columns": 2}


def test_analyze_output_json_writes_file(sample_csv, tmp_path):
    out_path = tmp_path / "out.json"
    _run(["analyze", str(sample_csv), "--output-json", str(out_path)])

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["shape"] == {"rows": 3, "columns": 2}


def test_analyze_html_flag_writes_report_html(sample_csv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _run(["analyze", str(sample_csv), "--html", "--quiet"])

    assert (tmp_path / "report.html").exists()
    assert "Data Detective Report" in (tmp_path / "report.html").read_text(encoding="utf-8")


def test_analyze_output_html_writes_given_path(sample_csv, tmp_path):
    out_path = tmp_path / "custom.html"
    _run(["analyze", str(sample_csv), "--output-html", str(out_path)])

    assert out_path.exists()


def test_analyze_markdown_flag_writes_report_md(sample_csv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _run(["analyze", str(sample_csv), "--markdown", "--quiet"])

    assert (tmp_path / "report.md").exists()
    assert "Data Detective Report" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_analyze_output_markdown_writes_given_path(sample_csv, tmp_path):
    out_path = tmp_path / "custom.md"
    _run(["analyze", str(sample_csv), "--output-markdown", str(out_path)])

    assert out_path.exists()


def test_version_flag_prints_version_and_exits_zero(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "data-detective" in out


def test_analyze_outlier_method_choice_rejected_by_argparse(sample_csv):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["analyze", str(sample_csv), "--outlier-method", "bogus"])


def test_analyze_missing_file_raises_data_load_error():
    parser = build_parser()
    args = parser.parse_args(["analyze", "/does/not/exist.csv"])
    from data_detective.exceptions import DataLoadError

    with pytest.raises(DataLoadError):
        args.func(args)


def test_main_no_subcommand_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["data-detective"])
    exit_code = main()

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "usage" in out.lower()


def test_main_handles_missing_file_gracefully(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["data-detective", "analyze", "/does/not/exist.csv"])
    exit_code = main()

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "File not found" in err


def test_main_handles_empty_file_gracefully(tmp_path, monkeypatch, capsys):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["data-detective", "analyze", str(empty_csv)])

    exit_code = main()

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "empty" in err.lower()


@pytest.fixture
def price_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "price.csv"
    csv_path.write_text("price,quantity\n10,5\n-5,3\n20,7\n", encoding="utf-8")
    return csv_path


@pytest.fixture
def price_rules_yaml(tmp_path: Path) -> Path:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        "column_overrides:\n  - column: price\n    category: negative_values\n    severity: failure\n"
    )
    return rules_path


def test_analyze_rules_flag_affects_health_score(price_csv, price_rules_yaml, capsys):
    _run(["analyze", str(price_csv), "--rules", str(price_rules_yaml), "--json", "--quiet"])

    report = json.loads(capsys.readouterr().out)
    assert "negative_values" in report["health_score"]["failures"]


def test_analyze_fail_on_failure_exits_nonzero(price_csv, price_rules_yaml, capsys):
    exit_code = _run(
        ["analyze", str(price_csv), "--rules", str(price_rules_yaml), "--fail-on", "failure", "--quiet"]
    )
    assert exit_code == 1
    assert "negative_values" in capsys.readouterr().err


def test_analyze_fail_on_failure_without_rules_exits_zero(price_csv, capsys):
    exit_code = _run(["analyze", str(price_csv), "--fail-on", "failure", "--quiet"])
    assert exit_code == 0


def test_analyze_missing_rules_file_raises_rules_error(sample_csv):
    from data_detective.rules import RulesError

    parser = build_parser()
    args = parser.parse_args(["analyze", str(sample_csv), "--rules", "/does/not/exist.yaml"])
    with pytest.raises(RulesError):
        args.func(args)


def test_main_handles_missing_rules_file_gracefully(sample_csv, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["data-detective", "analyze", str(sample_csv), "--rules", "/does/not/exist.yaml"])

    exit_code = main()

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "Could not read rules file" in err
