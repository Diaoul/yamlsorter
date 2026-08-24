from pathlib import Path

import pytest

from yamlsorter import ConfigError, ConfigManager, extract_key_order


def test_nested_list_entries_merge_like_top_level_ones() -> None:
    """Every entry of a template list describes the same section, at any depth."""
    orders = extract_key_order({"spec": {"deps": [{"a": {"x": 1}}, {"a": {"y": 2}}]}})

    assert orders["spec.deps.a"] == ["x", "y"]


def test_scalar_list_entries_are_ignored() -> None:
    orders = extract_key_order({"spec": {"components": ["a", "b"]}})

    assert "spec.components" not in orders


def test_chart_specific_type_falls_back_to_the_generic_helmrelease(config_dir: Path) -> None:
    config = ConfigManager(config_dir)

    assert config.has_template("helmrelease-cilium")
    assert not config.has_exact_template("helmrelease-cilium")
    assert config.load("helmrelease-cilium") == config.load("helmrelease")


def test_an_exact_template_wins_over_the_fallback(config_dir: Path) -> None:
    config = ConfigManager(config_dir)

    assert config.has_exact_template("helmrelease-apptemplate")
    assert config.load("helmrelease-apptemplate") != config.load("helmrelease")


def test_unknown_type_has_no_template(config_dir: Path) -> None:
    config = ConfigManager(config_dir)

    assert not config.has_template("httproute")
    with pytest.raises(ConfigError, match="no template for type"):
        _ = config.load("httproute")


def test_a_template_that_is_not_a_mapping_is_rejected(config_dir: Path) -> None:
    _ = (config_dir / "component.yaml.tpl").write_text("- a\n- b\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="not a mapping"):
        _ = ConfigManager(config_dir).load("component")


def test_an_unparseable_template_is_rejected(config_dir: Path) -> None:
    _ = (config_dir / "component.yaml.tpl").write_text("a: [unclosed\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="failed to read template"):
        _ = ConfigManager(config_dir).load("component")


def test_orders_are_loaded_once_per_type(config_dir: Path) -> None:
    config = ConfigManager(config_dir)
    first = config.load("helmrelease")
    (config_dir / "helmrelease.yaml.tpl").unlink()

    assert config.load("helmrelease") is first
