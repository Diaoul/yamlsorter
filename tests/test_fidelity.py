"""Rewrites must change key order and nothing else."""

import logging
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from fixtures import KS
from yamlsorter import Outcome, SortingTool, main
from yamlsorter.document import comment_damage, key_signature

ORDERED = """\
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
spec:
    sourceRef:
        kind: GitRepository
        name: home-ops
    path: ./p
    interval: 10m
    prune: true
"""


def test_a_file_already_in_template_order_is_left_alone(tmp_path: Path, config_dir: Path) -> None:
    """Its indentation is not this tool's business, so a reflow is not a change."""
    target = tmp_path / "ks.yaml"
    _ = target.write_text(ORDERED, encoding="utf-8")

    result = SortingTool(config_dir).processor.process(target)

    assert result.outcome is Outcome.UNCHANGED
    assert target.read_text(encoding="utf-8") == ORDERED


def test_check_passes_on_a_file_whose_order_is_already_right(
    tmp_path: Path, config_dir: Path
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(ORDERED, encoding="utf-8")

    assert main([str(target), "--config-dir", str(config_dir), "--check"]) == 0


def test_a_document_end_marker_survives(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS + "...\n", encoding="utf-8")

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    text = target.read_text(encoding="utf-8")
    assert text.rstrip().endswith("...")
    assert text.count("...") == 1


def test_a_comment_above_the_opening_marker_blocks_the_rewrite(
    tmp_path: Path, config_dir: Path
) -> None:
    """Ruamel drops it on load, so rewriting the file would lose it."""
    body = "# header\n" + KS
    target = tmp_path / "ks.yaml"
    _ = target.write_text(body, encoding="utf-8")

    result = SortingTool(config_dir).processor.process(target)

    assert result.outcome is Outcome.SKIPPED
    assert result.error == "round-trip would drop a comment"
    assert target.read_text(encoding="utf-8") == body


def test_the_majority_line_ending_wins_in_a_mixed_file(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_bytes(KS.replace("\n", "\r\n", 2).encode())

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    raw = target.read_bytes()
    assert b"\r" not in raw


def test_comment_damage_names_what_would_happen() -> None:
    assert comment_damage("# a\nx: 1\n", "x: 1\n") == "would drop a comment"
    assert comment_damage("x: 1\n", "# a\nx: 1\n") == "would re-anchor a comment"
    assert comment_damage("# a\nx: 1\ny: 2\n", "# a\ny: 2\nx: 1\n") == (
        "would move '# a' away from what it documents"
    )
    assert comment_damage("# a\nx: 1\ny: 2\n", "# a\nx: 1\ny: 2\n") is None


def test_key_signature_ignores_values_and_formatting(yaml: YAML) -> None:
    one = yaml.load("a: 1\nb:\n  c: 2\n")
    same = yaml.load("a: 9\nb: {c: 3}\n")
    other = yaml.load("b:\n  c: 2\na: 1\n")

    assert key_signature(one) == key_signature(same)
    assert key_signature(one) != key_signature(other)


def test_an_uppercase_chart_name_resolves_to_its_template(
    tmp_path: Path, config_dir: Path, yaml: YAML
) -> None:
    """`App-Template` and `app-template` are the same chart, so the same template."""
    target = tmp_path / "helmrelease.yaml"
    _ = target.write_text(
        "---\n"
        "apiVersion: helm.toolkit.fluxcd.io/v2\n"
        "kind: HelmRelease\n"
        "metadata:\n"
        "  name: app\n"
        "spec:\n"
        "  chartRef:\n"
        "    name: App-Template\n"
        "    kind: OCIRepository\n"
        "  values:\n"
        "    controllers:\n"
        "      app:\n"
        "        containers:\n"
        "          app:\n"
        "            resources: {}\n"
        "            image:\n"
        "              tag: v1\n"
        "              repository: repo\n",
        encoding="utf-8",
    )

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    doc = yaml.load(target.read_text(encoding="utf-8"))
    container = doc["spec"]["values"]["controllers"]["app"]["containers"]["app"]
    assert list(container["image"]) == ["repository", "tag"]


def test_a_chart_name_cannot_point_at_a_path_of_its_own(tmp_path: Path, config_dir: Path) -> None:
    """The name reaches the filesystem, so it may not carry separators."""
    from yamlsorter import FileTypeDetector

    file_type = FileTypeDetector.detect(
        {"kind": "HelmRelease", "spec": {"chartRef": {"name": "x/../../etc/passwd"}}}
    )

    assert file_type == "helmrelease-xetcpasswd"


def test_a_registered_template_invalidates_a_cached_fallback(
    tmp_path: Path, config_dir: Path
) -> None:
    from yamlsorter import ConfigManager

    config = ConfigManager(config_dir)
    assert config.load("helmrelease-cilium")["spec"][0] == "interval"

    replacement = tmp_path / "helmrelease.yaml"
    _ = replacement.write_text(
        "kind: HelmRelease\nspec:\n  chartRef: {}\n  interval: interval\n", encoding="utf-8"
    )
    _ = config.register(replacement, "helmrelease")

    assert config.load("helmrelease-cilium")["spec"][0] == "chartRef"


def test_the_auditor_ignores_keys_inherited_through_a_merge(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A merged key belongs to the anchor, which the template need not describe."""
    target = tmp_path / "ks.yaml"
    # The anchor lives under `annotations`, whose contents are user-chosen names the
    # auditor never reports, so `timeout` can only reach it through the merge.
    _ = target.write_text(
        "---\n"
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        "metadata:\n"
        "  name: app\n"
        "  annotations: &base\n"
        "    timeout: 5m\n"
        "spec:\n"
        "  <<: *base\n"
        "  path: ./p\n"
        "  prune: true\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.INFO):
        _ = SortingTool(config_dir).run([target], ["ks.yaml"], audit=True)

    assert "timeout" not in caplog.text
