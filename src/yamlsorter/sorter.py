"""Applying a template's key order to a parsed document."""

from __future__ import annotations

from typing import final

from ruamel.yaml.comments import CommentedMap

from yamlsorter.constants import ROOT_SECTION
from yamlsorter.document import own_items
from yamlsorter.models import YAMLValue
from yamlsorter.sections import matches, section_of
from yamlsorter.templates import KeyOrders


@final
class KeySorter:
    """Applies a template's key order to a parsed document, in place."""

    def sort_document(self, doc: CommentedMap, orders: KeyOrders) -> CommentedMap:
        """Reorder `doc` and every mapping under it, in place."""
        return self._sort_node(doc, orders, [])

    def _sort_node(
        self, node: dict[str, YAMLValue], orders: KeyOrders, path: list[str]
    ) -> CommentedMap:
        ordered = self._reorder(node, self._order_for(orders, path))

        for key, value in own_items(ordered):
            child = [*path, key]
            if isinstance(value, dict):
                ordered[key] = self._sort_node(value, orders, child)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        value[index] = self._sort_node(item, orders, child)

        return ordered

    @staticmethod
    def _reorder(node: dict[str, YAMLValue], order: list[str]) -> CommentedMap:
        """Rewrite a mapping in `order`, untemplated keys keeping their order after.

        A CommentedMap is refilled in place: comments, anchors, merge keys and flow
        style hang off the container, so replacing it would drop them. Only the
        mapping's own keys move -- keys inherited through `<<` stay with their anchor.
        """
        as_map = node if isinstance(node, CommentedMap) else CommentedMap(node)
        if not order:
            return as_map

        values = dict(own_items(as_map))
        templated = [key for key in order if key in values]
        if not templated:
            return as_map

        rest = [key for key in values if key not in order]
        target = [*templated, *rest]

        if list(values) == target:
            return as_map

        as_map.clear()
        for key in target:
            as_map[key] = values[key]
        return as_map

    @staticmethod
    def _order_for(orders: KeyOrders, path: list[str]) -> list[str]:
        if not path:
            return orders.get(ROOT_SECTION, [])

        section = section_of(path)
        if section in orders:
            return orders[section]

        # An exact section wins; failing that a `controllers.*.containers.*` pattern may.
        for candidate, order in orders.items():
            if matches(candidate, path):
                return order

        return []
