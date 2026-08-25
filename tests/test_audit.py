from pathlib import Path

from ruamel.yaml import YAML

from yamlsorter import ConfigManager, MissingKeyAuditor, Stats

HELMRELEASE = """\
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: app
spec:
  interval: 30m
  chartRef:
    kind: OCIRepository
    name: app-template
  driftDetection:
    mode: enabled
  values:
    controllers:
      app:
        containers:
          app:
            image:
              repository: repo
              tag: v1
            env:
              TZ: Europe/Paris
            probes:
              liveness: {}
"""


def audit(text: str, config_dir: Path, yaml: YAML) -> dict[str, set[str]]:
    docs = list(yaml.load_all(text))
    stats = Stats()
    MissingKeyAuditor(ConfigManager(config_dir)).audit(docs, stats)
    return stats.missing_keys


def test_untemplated_keys_are_reported(config_dir: Path, yaml: YAML) -> None:
    missing = audit(HELMRELEASE, config_dir, yaml)

    assert missing["helmrelease-apptemplate"] >= {"driftDetection", "mode", "probes"}


def test_names_standing_under_a_wildcard_are_not_missing(config_dir: Path, yaml: YAML) -> None:
    """`controllers."*"` covers whatever the manifest calls its controller."""
    missing = audit(HELMRELEASE, config_dir, yaml)["helmrelease-apptemplate"]

    assert "app" not in missing


def test_opaque_map_contents_are_not_missing(config_dir: Path, yaml: YAML) -> None:
    missing = audit(HELMRELEASE, config_dir, yaml)["helmrelease-apptemplate"]

    assert "TZ" not in missing


def test_all_caps_substitutions_are_not_missing(config_dir: Path, yaml: YAML) -> None:
    text = HELMRELEASE.replace("  interval: 30m\n", "  interval: 30m\n  APP_DOMAIN: example.com\n")

    missing = audit(text, config_dir, yaml)["helmrelease-apptemplate"]

    assert "APP_DOMAIN" not in missing


def test_all_caps_detection_can_be_turned_off(config_dir: Path, yaml: YAML) -> None:
    text = HELMRELEASE.replace("  interval: 30m\n", "  interval: 30m\n  APP_DOMAIN: example.com\n")
    stats = Stats()

    auditor = MissingKeyAuditor(ConfigManager(config_dir), all_caps=False)
    auditor.audit(list(yaml.load_all(text)), stats)

    assert "APP_DOMAIN" in stats.missing_keys["helmrelease-apptemplate"]


def test_marker_substrings_are_not_missing(config_dir: Path, yaml: YAML) -> None:
    text = HELMRELEASE.replace(
        "  name: app\n",
        "  name: app\n  annotations:\n    kustomize.toolkit.fluxcd.io/substitute: disabled\n",
        1,
    )
    stats = Stats()

    auditor = MissingKeyAuditor(
        ConfigManager(config_dir), ["kustomize.toolkit.fluxcd.io/substitute"]
    )
    auditor.audit(list(yaml.load_all(text)), stats)

    assert "kustomize.toolkit.fluxcd.io/substitute" not in stats.missing_keys.get(
        "helmrelease-apptemplate", set()
    )


def test_chart_values_are_skipped_without_a_chart_specific_template(
    config_dir: Path, yaml: YAML
) -> None:
    """The generic template does not describe spec.values, so it cannot judge it."""
    text = HELMRELEASE.replace("name: app-template", "name: cilium")

    missing = audit(text, config_dir, yaml)["helmrelease-cilium"]

    assert "controllers" not in missing
    assert "driftDetection" in missing


def test_documents_without_a_template_are_ignored(config_dir: Path, yaml: YAML) -> None:
    from fixtures import SECRET

    assert audit(SECRET, config_dir, yaml) == {}
