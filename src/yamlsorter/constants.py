"""Literals shared across the package."""

from __future__ import annotations

from typing import Final

#: Placeholder type on a result for a file no template applied to.
GENERIC: Final = "generic"

#: Template key standing in for whatever name the manifest uses at that level.
WILDCARD: Final = "*"

#: Section name for a template's top-level mapping.
ROOT_SECTION: Final = "root"

#: Separator joining a section path into a flat key.
PATH_SEP: Final = "."

# Templates named after their type are skeletons, not manifests: the suffix keeps
# repo-wide Flux scanners (Konflate, flux-local) from rendering the placeholder values
# as real resources. A template supplied by path is exempt -- it is already a real,
# valid manifest, so it has nothing to hide from.
TEMPLATE_SUFFIX: Final = ".yaml.tpl"

#: Suffixes a template in the config directory may carry, most specific first.
TEMPLATE_SUFFIXES: Final = (".yaml.tpl", ".yml.tpl", ".yaml", ".yml")

#: Filenames picked up when walking a directory.
DEFAULT_NAMES: Final = ("helmrelease.yaml", "kustomization.yaml", "ks.yaml")

#: Substrings marking a key as a substitution placeholder rather than schema.
DEFAULT_MARKERS: Final = ("kustomize.toolkit.fluxcd.io/substitute",)
