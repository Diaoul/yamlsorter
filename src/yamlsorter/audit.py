"""Reporting manifest keys no template mentions, so templates can be grown."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final, final

from ruamel.yaml.comments import CommentedMap

from yamlsorter.constants import WILDCARD
from yamlsorter.detect import FileTypeDetector
from yamlsorter.document import own_items
from yamlsorter.errors import ConfigError
from yamlsorter.models import Stats, YAMLValue
from yamlsorter.sections import matches
from yamlsorter.templates import ConfigManager

#: Keys inside these are user-chosen names, not schema, so they are never "missing".
OPAQUE_MAPS: Final[frozenset[str]] = frozenset(
    {"labels", "annotations", "matchLabels", "nodeSelector", "data", "stringData", "env"}
)


@final
class MissingKeyAuditor:
    """Reports manifest keys no template mentions, so templates can be grown."""

    def __init__(
        self,
        config: ConfigManager,
        markers: Iterable[str] = (),
        *,
        all_caps: bool = True,
    ) -> None:
        self.config = config
        self.markers = tuple(markers)
        self.all_caps = all_caps

    def audit(self, docs: Iterable[CommentedMap], stats: Stats) -> None:
        """Record every key of `docs` that its template does not mention."""
        for doc in docs:
            file_type = FileTypeDetector.detect(doc)
            if file_type is None or not self.config.has_template(file_type):
                continue

            try:
                orders = self.config.load(file_type)
            except ConfigError:
                continue

            known = {key for keys in orders.values() for key in keys if key != WILDCARD}
            wildcard_sections = {section for section, keys in orders.items() if WILDCARD in keys}

            # A chart-specific template covers spec.values; the generic one does not,
            # so auditing it there would flag every chart option as missing.
            skip_values = not self.config.has_exact_template(file_type)

            missing = self._keys(doc, [], wildcard_sections, skip_values) - known
            if missing:
                stats.missing_keys.setdefault(file_type, set()).update(missing)

    def _keys(
        self,
        node: dict[str, YAMLValue],
        path: list[str],
        wildcard_sections: set[str],
        skip_values: bool,
    ) -> set[str]:
        found: set[str] = set()

        for key, value in own_items(node):
            child = [*path, key]

            if skip_values and child[:2] == ["spec", "values"]:
                continue
            if self._is_substitution(key):
                continue

            # A name the template writes as `*` is not a missing key, but what sits
            # inside it is schema again, so keep descending.
            if not self._is_wildcard_name(child, wildcard_sections):
                found.add(key)
                if key in OPAQUE_MAPS:
                    continue

            if isinstance(value, dict):
                found |= self._keys(value, child, wildcard_sections, skip_values)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        found |= self._keys(item, child, wildcard_sections, skip_values)

        return found

    def _is_substitution(self, key: str) -> bool:
        """True for a key that names a substitution variable rather than a schema field."""
        if self.all_caps and key.isupper() and key.replace("_", "").isalpha():
            return True
        return any(marker in key for marker in self.markers)

    @staticmethod
    def _is_wildcard_name(path: list[str], wildcard_sections: set[str]) -> bool:
        """True for a name the template stands in for with `*` (an app, a container).

        Only the name level itself is covered: keys *inside* it are schema again, so
        an unlisted container field still shows up as missing.
        """
        parent = path[:-1]
        return any(matches(section, parent) for section in wildcard_sections)
