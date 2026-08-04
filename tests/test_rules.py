import sys

import pytest

from data_detective.rules import CategoryRule, HealthScoreRules, RulesError, load_rules


@pytest.fixture
def base_rules() -> HealthScoreRules:
    return HealthScoreRules(
        categories={
            "missing_values": CategoryRule(weight=25, severity="warning"),
            "negative_values": CategoryRule(weight=5, severity="warning"),
            "near_constant_columns": CategoryRule(weight=0, severity="info"),
        }
    )


def test_category_rule_rejects_invalid_severity():
    with pytest.raises(RulesError, match="Invalid severity"):
        CategoryRule(weight=5, severity="bogus")


def test_load_rules_overrides_category_weight_and_severity(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "categories:\n"
        "  missing_values:\n"
        "    weight: 40\n"
        "    severity: failure\n"
    )
    rules = load_rules(rules_file, base=base_rules)

    assert rules.categories["missing_values"].weight == 40
    assert rules.categories["missing_values"].severity == "failure"
    # Untouched categories keep the base's values.
    assert rules.categories["negative_values"].weight == 5
    assert rules.categories["negative_values"].severity == "warning"


def test_load_rules_unknown_category_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("categories:\n  totally_made_up:\n    weight: 10\n")

    with pytest.raises(RulesError, match="Unknown category"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_invalid_severity_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("categories:\n  missing_values:\n    severity: catastrophic\n")

    with pytest.raises(RulesError, match="Invalid severity"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_weight_sum_over_100_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("categories:\n  missing_values:\n    weight: 200\n")

    with pytest.raises(RulesError, match="exceeds 100"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_missing_file_raises(tmp_path, base_rules):
    with pytest.raises(RulesError, match="Could not read"):
        load_rules(tmp_path / "does_not_exist.yaml", base=base_rules)


def test_load_rules_malformed_yaml_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("categories: [this is not: valid: yaml")

    with pytest.raises(RulesError, match="Invalid YAML"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_non_mapping_top_level_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("- just\n- a\n- list\n")

    with pytest.raises(RulesError, match="YAML mapping"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_column_override_applies(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "column_overrides:\n"
        "  - column: price\n"
        "    category: negative_values\n"
        "    severity: failure\n"
    )
    rules = load_rules(rules_file, base=base_rules)

    override = rules.override_for("negative_values", "price")
    assert override is not None
    assert override.severity == "failure"
    assert rules.override_for("negative_values", "other_column") is None


def test_load_rules_column_override_unknown_category_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "column_overrides:\n"
        "  - column: price\n"
        "    category: totally_made_up\n"
    )
    with pytest.raises(RulesError, match="Unknown category"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_column_override_missing_fields_raises(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("column_overrides:\n  - column: price\n")

    with pytest.raises(RulesError, match="'column' and 'category'"):
        load_rules(rules_file, base=base_rules)


def test_load_rules_empty_file_returns_base_unchanged(tmp_path, base_rules):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("")

    rules = load_rules(rules_file, base=base_rules)
    assert rules.categories == base_rules.categories
    assert rules.column_overrides == []


def test_load_rules_without_pyyaml_installed_raises_actionable_error(tmp_path, base_rules, monkeypatch):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("categories:\n  missing_values:\n    weight: 40\n")

    monkeypatch.setitem(sys.modules, "yaml", None)

    with pytest.raises(RulesError, match=r"pip install data-detective-toolkit\[rules\]"):
        load_rules(rules_file, base=base_rules)
