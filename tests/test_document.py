from pathlib import Path

import pytest
from ruamel.yaml import YAML

from fixtures import KS
from yamlsorter import Outcome, SortingTool
from yamlsorter.document import own_items, read_text, write_text

MERGE = """\
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
x-common: &base
  prune: true
spec:
  <<: *base
  wait: true
  path: ./p
  interval: 10m
"""


def test_merged_keys_are_not_materialised(tmp_path: Path, config_dir: Path) -> None:
    """A key inherited through `<<` belongs to the anchor, not to the document."""
    target = tmp_path / "ks.yaml"
    _ = target.write_text(MERGE, encoding="utf-8")

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    text = target.read_text(encoding="utf-8")
    assert "<<:" in text
    # `prune` came from the merge; it must not gain an entry of its own.
    assert text.count("prune:") == 1


def test_merge_key_document_still_sorts_its_own_keys(
    tmp_path: Path, config_dir: Path, yaml: YAML
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(MERGE, encoding="utf-8")

    _ = SortingTool(config_dir).processor.process(target)

    doc = yaml.load(target.read_text(encoding="utf-8"))
    own = [key for key, _ in own_items(doc["spec"])]
    assert own == ["path", "interval", "wait"]


def test_empty_trailing_document_stays_empty(tmp_path: Path, config_dir: Path) -> None:
    """Dumping the `None` a bare `---` parses to would write a literal `null`."""
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS + "---\n", encoding="utf-8")

    _ = SortingTool(config_dir).processor.process(target)

    text = target.read_text(encoding="utf-8")
    assert "null" not in text
    assert text.endswith("---\n")


def test_crlf_line_endings_survive(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_bytes(KS.replace("\n", "\r\n").encode())

    assert SortingTool(config_dir).processor.process(target).outcome is Outcome.CHANGED

    raw = target.read_bytes()
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_lf_files_do_not_gain_carriage_returns(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS, encoding="utf-8")

    _ = SortingTool(config_dir).processor.process(target)

    assert b"\r" not in target.read_bytes()


def test_symlinked_manifest_is_written_through(tmp_path: Path, config_dir: Path) -> None:
    """Replacing the link with a regular file would silently detach it."""
    real = tmp_path / "real.yaml"
    _ = real.write_text(KS, encoding="utf-8")
    link = tmp_path / "ks.yaml"
    link.symlink_to(real)

    _ = SortingTool(config_dir).processor.process(link)

    assert link.is_symlink()
    assert "path: ./kubernetes" in real.read_text(encoding="utf-8")


def test_read_text_reports_the_ending_it_found(tmp_path: Path) -> None:
    target = tmp_path / "f.yaml"
    _ = target.write_bytes(b"a: 1\r\nb: 2\r\n")

    text, newline = read_text(target)

    assert newline == "\r\n"
    assert text == "a: 1\nb: 2\n"


def test_write_text_leaves_a_failed_write_without_stray_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "f.yaml"
    _ = target.write_text("a: 1\n", encoding="utf-8")

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("yamlsorter.document.shutil.move", boom)
    with pytest.raises(OSError, match="disk full"):
        write_text(target, "b: 2\n")

    assert target.read_text(encoding="utf-8") == "a: 1\n"
    assert list(tmp_path.iterdir()) == [target]


def test_own_items_accepts_a_plain_mapping() -> None:
    assert own_items({"b": 1, "a": 2}) == [("b", 1), ("a", 2)]


def test_an_unreadable_file_fails_rather_than_raising(tmp_path: Path, config_dir: Path) -> None:
    result = SortingTool(config_dir).processor.process(tmp_path / "absent.yaml")

    assert result.outcome is Outcome.FAILED
    assert result.error is not None


def test_a_failing_write_is_reported_as_a_failure(
    tmp_path: Path, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS, encoding="utf-8")

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr("yamlsorter.processor.write_text", boom)
    result = SortingTool(config_dir).processor.process(target)

    assert result.outcome is Outcome.FAILED
    assert result.error == "read-only file system"
