"""Value types and per-run bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import final

from yamlsorter.constants import GENERIC

type YAMLValue = str | int | float | bool | list["YAMLValue"] | dict[str, "YAMLValue"] | None


class Outcome(Enum):
    """What happened to one file."""

    CHANGED = "changed"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"


@final
@dataclass(frozen=True, slots=True)
class Result:
    """What one file's run amounted to."""

    path: Path
    outcome: Outcome
    file_type: str = GENERIC
    error: str | None = None


@final
@dataclass(slots=True)
class Stats:
    """Tallies across a run."""

    total: int = 0
    changed: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    missing_keys: dict[str, set[str]] = field(default_factory=dict)

    def record(self, result: Result) -> None:
        """Count one result."""
        self.total += 1
        match result.outcome:
            case Outcome.CHANGED:
                self.changed += 1
            case Outcome.UNCHANGED:
                self.unchanged += 1
            case Outcome.SKIPPED:
                self.skipped += 1
            case Outcome.FAILED:
                self.failed += 1
