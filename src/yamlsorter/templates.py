"""Loading templates and flattening them into per-section key orders."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import final

from ruamel.yaml import YAML

from yamlsorter.constants import TEMPLATE_SUFFIXES
from yamlsorter.detect import FileTypeDetector
from yamlsorter.errors import ConfigError
from yamlsorter.models import YAMLValue
from yamlsorter.sections import section_of

type KeyOrders = dict[str, list[str]]

#: A template supplied on the command line: the type it serves, or None to detect it.
type TemplateSpec = tuple[str | None, Path]


def extract_key_order(template: dict[str, YAMLValue]) -> KeyOrders:
    """Flatten a template manifest into {dotted.section: [keys in order]}."""
    orders: KeyOrders = {}

    def record(path: list[str], keys: list[str]) -> None:
        # A list in a template describes the shape of its entries, not their count,
        # so every entry contributes to one order for that section.
        section = orders.setdefault(section_of(path), [])
        section.extend(key for key in keys if key not in section)

    def walk(node: YAMLValue, path: list[str]) -> None:
        if not isinstance(node, dict):
            return

        record(path, list(node.keys()))

        for key, value in node.items():
            child = [*path, key]
            if isinstance(value, dict):
                walk(value, child)
            elif isinstance(value, list):
                for item in value:
                    walk(item, child)

    walk(template, [])
    return orders


@final
class ConfigManager:
    """Resolves a document type to a template, and a template to its key orders.

    Templates come from two places: files in the config directory named after the
    type they serve, and files registered by path. A registered template wins, and
    needs no particular name or suffix -- an ordinary manifest already in the repo
    is a valid template, since only its keys are read.
    """

    def __init__(self, config_dir: Path, templates: Iterable[TemplateSpec] = ()) -> None:
        self.config_dir = config_dir
        self._pending: list[TemplateSpec] = list(templates)
        self._registered: dict[str, Path] = {}
        self._orders: dict[str, KeyOrders] = {}
        self._yaml = YAML(typ="safe")

    def validate(self) -> None:
        """Raise ConfigError unless at least one usable template is reachable."""
        self._register_pending()
        if self._registered:
            return
        if not self.config_dir.is_dir():
            raise ConfigError(f"config directory not found: {self.config_dir}")
        found = (
            path for suffix in TEMPLATE_SUFFIXES for path in self.config_dir.glob(f"*{suffix}")
        )
        if next(found, None) is None:
            raise ConfigError(f"no templates in {self.config_dir}")

    def register(self, path: Path, file_type: str | None = None) -> str:
        """Use `path` as the template for a type, detecting the type if not given."""
        resolved = file_type or self.type_of(path)
        self._registered[resolved] = path
        # Other types may have cached orders through this one as a fallback.
        self._orders.clear()
        return resolved

    def type_of(self, path: Path) -> str:
        """The type a template file serves, read from its own `kind`."""
        document = self._read(path)
        file_type = FileTypeDetector.detect(document)
        if file_type is None:
            raise ConfigError(f"template {path} has no kind to derive a type from")
        return file_type

    def template_path(self, file_type: str) -> Path | None:
        """The file a type's order comes from, fallbacks included."""
        return self._resolve(file_type)

    def has_template(self, file_type: str) -> bool:
        """True when a template applies to the type, fallbacks included."""
        return self._resolve(file_type) is not None

    def has_exact_template(self, file_type: str) -> bool:
        """True when the type has its own template rather than a fallback."""
        return self._resolve_exact(file_type) is not None

    def load(self, file_type: str) -> KeyOrders:
        """Key orders for a type, read once and cached."""
        if file_type in self._orders:
            return self._orders[file_type]

        path = self._resolve(file_type)
        if path is None:
            raise ConfigError(f"no template for type {file_type!r} in {self.config_dir}")

        orders = extract_key_order(self._read(path))
        self._orders[file_type] = orders
        return orders

    def _read(self, path: Path) -> dict[str, YAMLValue]:
        try:
            with path.open(encoding="utf-8") as handle:
                template = next(iter(self._yaml.load_all(handle)), None)
        except Exception as exc:
            raise ConfigError(f"failed to read template {path}: {exc}") from exc

        if not isinstance(template, dict):
            raise ConfigError(f"template {path} is not a mapping")
        return template

    def _register_pending(self) -> None:
        while self._pending:
            file_type, path = self._pending.pop(0)
            _ = self.register(path, file_type)

    def _resolve(self, file_type: str) -> Path | None:
        exact = self._resolve_exact(file_type)
        if exact is not None:
            return exact
        # A chart-specific HelmRelease falls back to the generic one, so a repo only
        # writes a chart template when that chart deserves its own ordering.
        if file_type.startswith("helmrelease-"):
            return self._resolve_exact("helmrelease")
        return None

    def _resolve_exact(self, file_type: str) -> Path | None:
        self._register_pending()
        registered = self._registered.get(file_type)
        if registered is not None:
            return registered
        for suffix in TEMPLATE_SUFFIXES:
            candidate = self.config_dir / f"{file_type}{suffix}"
            if candidate.is_file():
                return candidate
        return None
