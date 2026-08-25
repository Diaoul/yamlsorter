"""Naming the template a document should be sorted against."""

from __future__ import annotations

from typing import final

from yamlsorter.models import YAMLValue


@final
class FileTypeDetector:
    """Names the template a document should be sorted against."""

    @classmethod
    def detect(cls, data: dict[str, YAMLValue]) -> str | None:
        """Name the template type for one document, or None when it has no `kind`.

        Any `kind` yields a type: `HTTPRoute` is `httproute`, so a template can be
        supplied for it. Whether one exists is the config's business, not the
        detector's.
        """
        kind = data.get("kind")
        if not isinstance(kind, str) or not kind:
            return None

        if kind == "HelmRelease":
            chart = cls._chart_name(data)
            return f"helmrelease-{chart}" if chart else "helmrelease"

        if kind == "Kustomization":
            api_version = data.get("apiVersion")
            is_flux = isinstance(api_version, str) and "kustomize.toolkit.fluxcd.io" in api_version
            return "flux-kustomization" if is_flux else "kustomization"

        return cls.slug(kind)

    @staticmethod
    def slug(kind: str) -> str:
        """Reduce a `kind` to the name its template file carries."""
        return "".join(char for char in kind if char.isalnum()).lower()

    @classmethod
    def _chart_name(cls, data: dict[str, YAMLValue]) -> str | None:
        """Chart backing a HelmRelease, via chartRef (this repo) or inline chart.

        The name reaches the filesystem as `helmrelease-<chart>.yaml.tpl`, so it goes
        through the same slug as any other kind: a chart called `App-Template` resolves
        to the template `app-template` does, and a name carrying `/` or `..` cannot
        point the lookup at a path of its own choosing.
        """
        spec = data.get("spec")
        if not isinstance(spec, dict):
            return None

        chart_ref = spec.get("chartRef")
        if isinstance(chart_ref, dict):
            name = chart_ref.get("name")
            if isinstance(name, str):
                return cls.slug(name) or None

        chart = spec.get("chart")
        if isinstance(chart, dict):
            chart_spec = chart.get("spec")
            if isinstance(chart_spec, dict):
                name = chart_spec.get("chart")
                if isinstance(name, str):
                    return cls.slug(name) or None

        return None
