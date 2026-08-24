"""Parsing, sorting and rewriting one file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import final

from ruamel.yaml.comments import CommentedMap

from yamlsorter.detect import FileTypeDetector
from yamlsorter.document import LF, detached_comment, read_text, render, write_text, yaml_reader
from yamlsorter.errors import ConfigError, ParseError
from yamlsorter.models import Outcome, Result, YAMLValue
from yamlsorter.sorter import KeySorter
from yamlsorter.templates import ConfigManager


@final
@dataclass(frozen=True, slots=True)
class ParsedFile:
    """One file as read: its text, its line ending and its document stream."""

    path: Path
    text: str
    newline: str
    docs: list[YAMLValue]

    @property
    def mappings(self) -> list[CommentedMap]:
        """The documents that are mappings; anything else cannot be sorted."""
        return [doc for doc in self.docs if isinstance(doc, CommentedMap)]


@final
class FileProcessor:
    """Parses, sorts and rewrites one file."""

    def __init__(self, sorter: KeySorter, config: ConfigManager, dry_run: bool) -> None:
        self.sorter = sorter
        self.config = config
        self.dry_run = dry_run
        self._yaml = yaml_reader()

    def read(self, path: Path) -> ParsedFile:
        """Load a file's document stream, or raise ParseError."""
        try:
            text, newline = read_text(path)
        except OSError as exc:
            raise ParseError(str(exc)) from exc

        try:
            docs = list(self._yaml.load_all(text))
        except Exception as exc:
            raise ParseError(f"unparseable: {exc}") from exc

        return ParsedFile(path, text, newline, docs)

    def process(self, path: Path) -> Result:
        """Read and sort one file. Convenience wrapper around read() and sort()."""
        try:
            parsed = self.read(path)
        except ParseError as exc:
            return Result(path, Outcome.FAILED, error=str(exc))
        return self.sort(parsed)

    def sort(self, parsed: ParsedFile) -> Result:
        """Sort an already parsed file, rewriting it unless this is a dry run."""
        path = parsed.path
        typed = [(doc, FileTypeDetector.detect(doc)) for doc in parsed.mappings]
        sortable = [
            (doc, kind)
            for doc, kind in typed
            if kind is not None and self.config.has_template(kind)
        ]
        if not sortable:
            return Result(path, Outcome.SKIPPED)

        file_type = sortable[0][1]
        try:
            for doc, kind in sortable:
                _ = self.sorter.sort_document(doc, self.config.load(kind))
        except ConfigError as exc:
            return Result(path, Outcome.FAILED, file_type, str(exc))

        explicit_start = parsed.text.lstrip().startswith("---")
        rendered = render(self._yaml, parsed.docs, explicit_start=explicit_start)
        if rendered.strip() == parsed.text.strip():
            return Result(path, Outcome.UNCHANGED, file_type)

        moved = detached_comment(parsed.text, rendered)
        if moved:
            return Result(
                path,
                Outcome.SKIPPED,
                file_type,
                f"round-trip would move {moved} away from what it documents",
            )

        if not self.dry_run:
            try:
                write_text(path, rendered, parsed.newline or LF)
            except OSError as exc:
                return Result(path, Outcome.FAILED, file_type, str(exc))

        return Result(path, Outcome.CHANGED, file_type)
