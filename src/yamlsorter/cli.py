"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from yamlsorter.constants import DEFAULT_MARKERS, DEFAULT_NAMES
from yamlsorter.templates import TemplateSpec
from yamlsorter.tool import SortingTool
from yamlsorter.version import __version__


def template_spec(value: str) -> TemplateSpec:
    """Parse `--template PATH` or `--template TYPE=PATH`.

    A leading `TYPE=` is only read as one when it could not be part of a path, so
    `--template ./some=dir/helmrelease.yaml` still means a path.
    """
    name, separator, rest = value.partition("=")
    if separator and name and "/" not in name and os.sep not in name:
        return name, Path(rest)
    return None, Path(value)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="yamlsorter",
        description="Reorder keys in Flux manifests to match per-type templates.",
    )
    _ = parser.add_argument("paths", type=Path, nargs="+", help="files or directories to sort")
    _ = parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(".yamlsorter"),
        help="directory of template manifests (default: %(default)s)",
    )
    _ = parser.add_argument(
        "--template",
        type=template_spec,
        action="append",
        default=[],
        metavar="[TYPE=]PATH",
        help=(
            "use an ordinary manifest as the template for its own kind, or for TYPE; "
            "repeatable, and takes precedence over the config directory"
        ),
    )
    _ = parser.add_argument(
        "--check",
        "--dry-run",
        action="store_true",
        help="report what would change without writing, exit 1 if anything would",
    )
    _ = parser.add_argument(
        "--names",
        nargs="+",
        default=list(DEFAULT_NAMES),
        metavar="NAME",
        help="filenames to pick up when walking directories (default: %(default)s)",
    )
    _ = parser.add_argument(
        "--audit",
        action="store_true",
        help="also list manifest keys no template mentions",
    )
    _ = parser.add_argument("--verbose", "-v", action="store_true", help="log skipped files too")
    _ = parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the sorter, returning the process exit code."""
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )

    tool = SortingTool(
        config_dir=args.config_dir,
        templates=args.template,
        dry_run=args.check,
        markers=DEFAULT_MARKERS,
    )
    return tool.run(args.paths, args.names, audit=args.audit)
