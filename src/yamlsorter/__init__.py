"""Reorder keys in Kubernetes and Flux manifests to match per-type templates.

Key order is not semantic to Kubernetes, but a stable order makes diffs readable
and reviews mechanical. The desired order is declared by example: a template is a
manifest whose *keys* define the order for its type -- a skeleton in the config
directory, or an ordinary manifest supplied by path. Values are ignored either way.

Keys absent from a template keep their relative order and sort after the templated
ones, so a template never has to be exhaustive.
"""

from __future__ import annotations

from yamlsorter.audit import MissingKeyAuditor
from yamlsorter.cli import build_parser, main
from yamlsorter.constants import (
    DEFAULT_MARKERS,
    DEFAULT_NAMES,
    PATH_SEP,
    ROOT_SECTION,
    TEMPLATE_SUFFIX,
    WILDCARD,
)
from yamlsorter.detect import FileTypeDetector
from yamlsorter.errors import ConfigError, ParseError, YAMLSorterError
from yamlsorter.models import Outcome, Result, Stats, YAMLValue
from yamlsorter.processor import FileProcessor, ParsedFile
from yamlsorter.sorter import KeySorter
from yamlsorter.templates import ConfigManager, KeyOrders, TemplateSpec, extract_key_order
from yamlsorter.tool import SortingTool
from yamlsorter.version import __version__

__all__ = [
    "DEFAULT_MARKERS",
    "DEFAULT_NAMES",
    "PATH_SEP",
    "ROOT_SECTION",
    "TEMPLATE_SUFFIX",
    "WILDCARD",
    "ConfigError",
    "ConfigManager",
    "FileProcessor",
    "FileTypeDetector",
    "KeyOrders",
    "KeySorter",
    "MissingKeyAuditor",
    "Outcome",
    "ParseError",
    "ParsedFile",
    "Result",
    "SortingTool",
    "Stats",
    "TemplateSpec",
    "YAMLSorterError",
    "YAMLValue",
    "__version__",
    "build_parser",
    "extract_key_order",
    "main",
]
