"""Driving a run over a set of paths."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import final

from yamlsorter.audit import MissingKeyAuditor
from yamlsorter.constants import DEFAULT_MARKERS, DEFAULT_NAMES
from yamlsorter.errors import ConfigError, ParseError
from yamlsorter.models import Outcome, Result, Stats
from yamlsorter.processor import FileProcessor
from yamlsorter.sorter import KeySorter
from yamlsorter.templates import ConfigManager, TemplateSpec

log = logging.getLogger(__name__)

#: Exit code for a run that hit an error.
EXIT_ERROR = 2
#: Exit code for a check run that found something to sort.
EXIT_UNSORTED = 1


@final
class SortingTool:
    """Sorts every matching file under a set of paths."""

    def __init__(
        self,
        config_dir: Path,
        *,
        templates: Iterable[TemplateSpec] = (),
        dry_run: bool = False,
        markers: Iterable[str] = DEFAULT_MARKERS,
        all_caps: bool = True,
    ) -> None:
        self.config = ConfigManager(config_dir, templates)
        self.sorter = KeySorter()
        self.processor = FileProcessor(self.sorter, self.config, dry_run)
        self.auditor = MissingKeyAuditor(self.config, markers, all_caps=all_caps)
        self.dry_run = dry_run

    def run(
        self,
        paths: Sequence[Path],
        names: Sequence[str] = DEFAULT_NAMES,
        *,
        audit: bool = False,
    ) -> int:
        """Sort every matching file, returning the process exit code."""
        try:
            self.config.validate()
        except ConfigError as exc:
            log.error("%s", exc)
            return EXIT_ERROR

        files = sorted(set(self._collect(paths, names)))
        if not files:
            log.warning("no matching files found")
            return 0

        stats = Stats()
        for path in files:
            stats.record(self._process(path, stats, audit=audit))

        self._report(stats)
        if stats.failed:
            return EXIT_ERROR
        # In check mode an unsorted file is the finding, so it has to fail the run.
        return EXIT_UNSORTED if self.dry_run and stats.changed else 0

    def _process(self, path: Path, stats: Stats, *, audit: bool) -> Result:
        try:
            parsed = self.processor.read(path)
        except ParseError as exc:
            result = Result(path, Outcome.FAILED, error=str(exc))
        else:
            result = self.processor.sort(parsed)
            if audit:
                # Auditing is advisory: a template that cannot be read is not a failure.
                self.auditor.audit(parsed.mappings, stats)

        self._log(result)
        return result

    def _log(self, result: Result) -> None:
        match result.outcome:
            case Outcome.CHANGED:
                log.info(
                    "%s %s (%s)",
                    "would sort" if self.dry_run else "sorted",
                    result.path,
                    result.file_type,
                )
            case Outcome.FAILED:
                log.error("%s: %s", result.path, result.error)
            case Outcome.SKIPPED if result.error:
                log.warning("skipped %s: %s", result.path, result.error)
            case Outcome.SKIPPED:
                log.debug("skipped %s", result.path)
            case Outcome.UNCHANGED:
                log.debug("unchanged %s", result.path)

    @staticmethod
    def _collect(paths: Sequence[Path], names: Sequence[str]) -> Iterator[Path]:
        """Yield the files to sort. Explicit file arguments bypass the name filter."""
        wanted = set(names)
        for path in paths:
            if path.is_file():
                yield path
            elif path.is_dir():
                for root, dirs, filenames in os.walk(path):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    yield from (Path(root) / name for name in filenames if name in wanted)
            else:
                log.warning("no such path: %s", path)

    def _report(self, stats: Stats) -> None:
        log.info(
            "%d files: %d %s, %d unchanged, %d skipped, %d failed",
            stats.total,
            stats.changed,
            "to sort" if self.dry_run else "sorted",
            stats.unchanged,
            stats.skipped,
            stats.failed,
        )

        for file_type, keys in sorted(stats.missing_keys.items()):
            template = self.config.template_path(file_type)
            log.info(
                "keys absent from %s: %s",
                template if template else file_type,
                ", ".join(sorted(keys)),
            )
