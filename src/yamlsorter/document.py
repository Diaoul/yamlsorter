"""Reading, rendering and rewriting YAML text without losing what it carries."""

from __future__ import annotations

import io
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from yamlsorter.models import YAMLValue

CRLF = "\r\n"
LF = "\n"


def yaml_reader() -> YAML:
    """Round-trip parser. Comments, anchors and quoting survive a load/dump cycle."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.map_indent = 2
    yaml.sequence_indent = 4
    yaml.sequence_dash_offset = 2
    yaml.width = 4096
    yaml.default_flow_style = None
    return yaml


def own_items(node: dict[str, YAMLValue]) -> list[tuple[str, YAMLValue]]:
    """The mapping's own keys, excluding any inherited through a `<<` merge.

    Merged keys are not the document's to move: materialising them would sever
    the link to the anchor they came from.
    """
    if isinstance(node, CommentedMap):
        return list(node.non_merged_items())
    return list(node.items())


def read_text(path: Path) -> tuple[str, str]:
    """Return the file's text with LF endings, plus the ending it actually used.

    Newlines are normalised for parsing and restored on write, so a CRLF repo does
    not get a whole-file diff out of a key reorder.
    """
    with path.open(encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = CRLF if CRLF in raw else LF
    return raw.replace(CRLF, LF), newline


def write_text(path: Path, content: str, newline: str = LF) -> None:
    """Replace the file atomically, keeping its permissions and following symlinks."""
    target = path.resolve() if path.is_symlink() else path
    mode = target.stat().st_mode
    if newline != LF:
        content = content.replace(LF, newline)

    tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed below; handle kept for cleanup
        mode="w",
        dir=target.parent,
        delete=False,
        encoding="utf-8",
        newline="",
        suffix=".yamlsorter",
    )
    try:
        with tmp:
            _ = tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        Path(tmp.name).chmod(mode & 0o7777)
        shutil.move(tmp.name, target)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise


def render(yaml: YAML, docs: list[YAMLValue], *, explicit_start: bool) -> str:
    """Serialise a document stream, keeping empty documents empty."""
    buffer = io.StringIO()
    for index, doc in enumerate(docs):
        if index > 0 or explicit_start:
            _ = buffer.write("---\n")
        # An empty document has no body: dumping `None` would write a literal `null`.
        if doc is None:
            continue
        yaml.dump(doc, buffer)
    return buffer.getvalue()


def _comment_anchors(text: str) -> Iterator[tuple[str, str]]:
    """Pair every comment with the first line of content beneath it."""
    lines = [line.strip() for line in text.splitlines()]

    for index, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        following = next(
            (later for later in lines[index + 1 :] if later and not later.startswith("#")),
            "",
        )
        yield line, following


def detached_comment(original: str, rendered: str) -> str | None:
    """Name a comment the round-trip re-anchored, if any.

    ruamel cannot faithfully re-emit a comment that sits after a list dash
    (`- # note`): it reattaches to the preceding entry, so the note ends up
    describing the wrong item. Rewriting such a file would silently mislead.
    """
    before = list(_comment_anchors(original))
    after = list(_comment_anchors(rendered))

    if len(before) != len(after):
        return "a comment"

    for (comment, was), (_, now) in zip(before, after, strict=True):
        if was != now:
            return repr(comment)

    return None
