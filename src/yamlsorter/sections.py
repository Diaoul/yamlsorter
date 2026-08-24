"""Flat section paths, and matching them against wildcard patterns."""

from __future__ import annotations

from yamlsorter.constants import PATH_SEP, ROOT_SECTION, WILDCARD


def section_of(path: list[str]) -> str:
    """Flatten a key path into the section name templates are keyed by."""
    return PATH_SEP.join(path) if path else ROOT_SECTION


def matches(pattern: str, path: list[str]) -> bool:
    """True when a section pattern describes `path`.

    A literal component matches exactly; `*` matches whatever the manifest called
    that level, so `controllers.*.containers` describes every controller.
    """
    parts = pattern.split(PATH_SEP)
    if len(parts) != len(path):
        return False
    return all(part in (WILDCARD, actual) for part, actual in zip(parts, path, strict=True))
