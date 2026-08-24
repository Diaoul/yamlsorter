import logging
from pathlib import Path

import pytest

from fixtures import KS, SECRET
from yamlsorter import Outcome, Result, SortingTool, Stats
from yamlsorter.tool import EXIT_ERROR, EXIT_UNSORTED


def test_no_matching_files_is_not_a_failure(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    empty = tmp_path / "tree"
    empty.mkdir()

    with caplog.at_level(logging.WARNING):
        assert SortingTool(config_dir).run([empty]) == 0

    assert "no matching files found" in caplog.text


def test_a_path_that_does_not_exist_is_reported(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert SortingTool(config_dir).run([tmp_path / "absent"]) == 0

    assert "no such path" in caplog.text


def test_an_unparseable_file_fails_the_run(tmp_path: Path, config_dir: Path) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text("apiVersion: [unclosed\n", encoding="utf-8")

    assert SortingTool(config_dir).run([target]) == EXIT_ERROR


def test_default_names_are_used_when_none_are_given(tmp_path: Path, config_dir: Path) -> None:
    _ = (tmp_path / "ks.yaml").write_text(KS, encoding="utf-8")
    _ = (tmp_path / "other.yaml").write_text(KS, encoding="utf-8")

    assert SortingTool(config_dir, dry_run=True).run([tmp_path]) == EXIT_UNSORTED
    assert (tmp_path / "other.yaml").read_text(encoding="utf-8") == KS


def test_audit_reports_missing_keys(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS.replace("  interval: 10m\n", "  interval: 10m\n  timeout: 5m\n"))

    with caplog.at_level(logging.INFO):
        assert SortingTool(config_dir).run([target], audit=True) == 0

    assert "flux-kustomization.yaml.tpl: timeout" in caplog.text


def test_audit_stays_quiet_when_the_template_covers_everything(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(KS, encoding="utf-8")

    with caplog.at_level(logging.INFO):
        _ = SortingTool(config_dir).run([target], audit=True)

    assert "keys absent" not in caplog.text


def test_skipped_files_are_logged_with_their_reason(
    tmp_path: Path, config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / "ks.yaml"
    _ = target.write_text(SECRET, encoding="utf-8")

    with caplog.at_level(logging.DEBUG):
        assert SortingTool(config_dir).run([target]) == 0

    assert "skipped" in caplog.text


def test_stats_count_every_outcome() -> None:
    stats = Stats()
    for outcome in Outcome:
        stats.record(Result(Path("f.yaml"), outcome))

    assert (stats.total, stats.changed, stats.unchanged, stats.skipped, stats.failed) == (
        4,
        1,
        1,
        1,
        1,
    )
