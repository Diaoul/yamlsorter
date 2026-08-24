import logging
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from fixtures import KS
from yamlsorter import ConfigError, ConfigManager, Outcome, SortingTool, main
from yamlsorter.cli import template_spec
from yamlsorter.tool import EXIT_ERROR

HTTPROUTE = """\
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
spec:
  rules:
    - backendRefs:
        - name: app
          port: 80
  hostnames: ["app.example.com"]
  parentRefs:
    - name: internal
"""

HTTPROUTE_TEMPLATE = """\
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: name
spec:
  parentRefs:
    - name: name
  hostnames: []
  rules:
    - backendRefs:
        - name: name
          port: 80
"""


def test_any_kind_gets_a_type(tmp_path: Path, config_dir: Path, yaml: YAML) -> None:
    """A plain manifest, registered by path, orders every document of its kind."""
    template = tmp_path / "template-httproute.yaml"
    _ = template.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    target = tmp_path / "httproute.yaml"
    _ = target.write_text(HTTPROUTE, encoding="utf-8")

    tool = SortingTool(config_dir, templates=[(None, template)])
    assert tool.processor.process(target).outcome is Outcome.CHANGED

    doc = yaml.load(target.read_text(encoding="utf-8"))
    assert list(doc["spec"]) == ["parentRefs", "hostnames", "rules"]


def test_a_type_can_be_named_explicitly(tmp_path: Path, config_dir: Path, yaml: YAML) -> None:
    """The template's own kind is a default, not a constraint."""
    template = tmp_path / "skeleton.yaml"
    _ = template.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    target = tmp_path / "route.yaml"
    _ = target.write_text(HTTPROUTE.replace("kind: HTTPRoute", "kind: TCPRoute"), encoding="utf-8")

    tool = SortingTool(config_dir, templates=[("tcproute", template)])
    assert tool.processor.process(target).outcome is Outcome.CHANGED

    doc = yaml.load(target.read_text(encoding="utf-8"))
    assert next(iter(doc["spec"])) == "parentRefs"


def test_a_registered_template_beats_the_config_directory(
    tmp_path: Path, config_dir: Path, yaml: YAML
) -> None:
    template = tmp_path / "other.yaml"
    _ = template.write_text(
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        "spec:\n"
        "  wait: wait\n"
        "  prune: prune\n",
        encoding="utf-8",
    )
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS, encoding="utf-8")

    tool = SortingTool(config_dir, templates=[(None, template)])
    _ = tool.processor.process(target)

    doc = yaml.load(target.read_text(encoding="utf-8"))
    assert list(doc["spec"])[:2] == ["wait", "prune"]


def test_a_plain_yaml_template_in_the_config_directory_is_used(
    tmp_path: Path, config_dir: Path, yaml: YAML
) -> None:
    _ = (config_dir / "httproute.yaml").write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    target = tmp_path / "httproute.yaml"
    _ = target.write_text(HTTPROUTE, encoding="utf-8")

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    doc = yaml.load(target.read_text(encoding="utf-8"))
    assert next(iter(doc["spec"])) == "parentRefs"


def test_the_tpl_suffix_wins_over_a_plain_one(tmp_path: Path, config_dir: Path) -> None:
    _ = (config_dir / "flux-kustomization.yaml").write_text("kind: Kustomization\n")
    config = ConfigManager(config_dir)

    path = config.template_path("flux-kustomization")

    assert path is not None
    assert path.name == "flux-kustomization.yaml.tpl"


def test_templates_alone_need_no_config_directory(tmp_path: Path) -> None:
    template = tmp_path / "template.yaml"
    _ = template.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    target = tmp_path / "httproute.yaml"
    _ = target.write_text(HTTPROUTE, encoding="utf-8")

    tool = SortingTool(tmp_path / "absent", templates=[(None, template)])

    assert tool.run([target], ["httproute.yaml"]) == 0


def test_a_template_without_a_kind_is_rejected(tmp_path: Path) -> None:
    template = tmp_path / "template.yaml"
    _ = template.write_text("a: 1\n", encoding="utf-8")
    config = ConfigManager(tmp_path, [(None, template)])

    with pytest.raises(ConfigError, match="no kind to derive a type from"):
        config.validate()


def test_a_missing_template_file_fails_the_run(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS, encoding="utf-8")

    tool = SortingTool(config_dir, templates=[(None, tmp_path / "absent.yaml")])

    assert tool.run([target], ["ks.yaml"]) == EXIT_ERROR


def test_registering_a_type_twice_uses_the_last_template(tmp_path: Path, config_dir: Path) -> None:
    first = tmp_path / "first.yaml"
    _ = first.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    second = tmp_path / "second.yaml"
    _ = second.write_text(
        "apiVersion: gateway.networking.k8s.io/v1\n"
        "kind: HTTPRoute\n"
        "spec:\n"
        "  rules: []\n"
        "  parentRefs: []\n",
        encoding="utf-8",
    )
    config = ConfigManager(config_dir, [(None, first)])
    _ = config.load("httproute")

    _ = config.register(second)

    assert config.template_path("httproute") == second
    assert config.load("httproute")["spec"][0] == "rules"


def test_audit_names_the_template_a_type_came_from(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:

    template = tmp_path / "template.yaml"
    _ = template.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    target = tmp_path / "httproute.yaml"
    _ = target.write_text(HTTPROUTE.replace("  hostnames:", "  timeouts: {}\n  hostnames:"))

    tool = SortingTool(config_dir, templates=[(None, template)])
    with caplog.at_level(logging.INFO):
        _ = tool.run([target], ["httproute.yaml"], audit=True)

    assert f"keys absent from {template}: timeouts" in caplog.text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("some/helmrelease.yaml", (None, Path("some/helmrelease.yaml"))),
        ("helmrelease=some/file.yaml", ("helmrelease", Path("some/file.yaml"))),
        ("./some=dir/file.yaml", (None, Path("./some=dir/file.yaml"))),
        ("=file.yaml", (None, Path("=file.yaml"))),
    ],
)
def test_template_spec_parsing(value: str, expected: tuple[str | None, Path]) -> None:
    assert template_spec(value) == expected


def test_cli_accepts_repeated_templates(tmp_path: Path, config_dir: Path) -> None:
    route_template = tmp_path / "route.yaml"
    _ = route_template.write_text(HTTPROUTE_TEMPLATE, encoding="utf-8")
    route = tmp_path / "httproute.yaml"
    _ = route.write_text(HTTPROUTE, encoding="utf-8")
    ks = tmp_path / "ks.yaml"
    _ = ks.write_text(KS, encoding="utf-8")

    status = main(
        [
            str(route),
            str(ks),
            "--config-dir",
            str(config_dir),
            "--template",
            str(route_template),
            "--check",
        ]
    )

    assert status == 1
    assert route.read_text(encoding="utf-8") == HTTPROUTE
