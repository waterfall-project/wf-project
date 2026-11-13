# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spread of the end-to-end paths over the parts of the chain, by measured duration."""

import json
from typing import TYPE_CHECKING

import pytest

from wftools import e2eparts

if TYPE_CHECKING:
    from pathlib import Path

SEPARATOR = e2eparts.SEPARATOR
LISTING = """\
Listing tests:
  [chromium] \u203a admin.spec.ts:41:1 \u203a reaches a screen
  [chromium] \u203a grid.spec.ts:10:1 \u203a edits a cell
  [chromium] \u203a grid.spec.ts:30:1 \u203a pastes a column
  [chromium] \u203a map.spec.ts:5:1 \u203a zooms
  [chromium] \u203a wide.spec.ts:8:1 \u203a first \u203a one
  [chromium] \u203a wide.spec.ts:8:1 \u203a first \u203a two
  [chromium] \u203a wide.spec.ts:8:1 \u203a second
Total: 7 tests in 4 files
"""
LOG = """\
T \x1b[32m✓\x1b[39m    1 [chromium] \u203a e2e/admin.spec.ts:41:1 \u203a reaches a screen (8.3s)
T ✓    2 [chromium] \u203a e2e/grid.spec.ts:10:1 \u203a edits a cell (350ms)
T ✓    3 [chromium] \u203a e2e/grid.spec.ts:30:1 \u203a pastes a column (1.5s)
T ✘    4 [chromium] \u203a e2e/map.spec.ts:5:1 \u203a zooms (1.2m)
T -    5 [chromium] \u203a e2e/map.spec.ts:9:1 \u203a skipped one
T ✓    6 [chromium] \u203a e2e/wide.spec.ts:8:1 \u203a first \u203a one (2.0s)
T ✓    7 [chromium] \u203a e2e/wide.spec.ts:8:1 \u203a first \u203a two (3.0s)
T 87 passed (2.8m)
"""


def parallel(file: str) -> bool:
    return file == "wide.spec.ts"


def played(plans: list[list[str]], listing: str = LISTING) -> list[tuple[str, str]]:
    """Return the (file, title) pairs a test list plays: a file line plays all of its tests."""
    pairs: list[tuple[str, str]] = []
    for line in plans:
        for entry in line:
            file, _, title = entry.partition(SEPARATOR)
            pairs.extend(
                (name, text)
                for name, text, _ in e2eparts.listed(listing)
                if name == file and (not title or text == title)
            )
    return pairs


def test_a_listing_gives_its_tests_and_a_log_their_seconds() -> None:
    assert [(file, title) for file, title, _ in e2eparts.listed(LISTING)][:2] == [
        ("admin.spec.ts", "reaches a screen"),
        ("grid.spec.ts", "edits a cell"),
    ]
    seconds = {title: value for _, title, value in e2eparts.listed(LOG, timed=True)}
    assert seconds["reaches a screen"] == pytest.approx(8.3)
    assert seconds["edits a cell"] == pytest.approx(0.35)
    assert seconds["zooms"] == pytest.approx(72.0)
    assert "skipped one" not in seconds


def test_the_seconds_of_a_file_are_summed_and_a_parallel_file_is_kept_test_by_test() -> None:
    measured = e2eparts.measure(LOG, parallel)
    assert measured == {
        "admin.spec.ts": 8.3,
        "grid.spec.ts": 1.9,
        "map.spec.ts": 72.0,
        f"wide.spec.ts{SEPARATOR}first{SEPARATOR}one": 2.0,
        f"wide.spec.ts{SEPARATOR}first{SEPARATOR}two": 3.0,
    }


def test_the_heavy_file_is_alone_in_its_part() -> None:
    durations = {"admin.spec.ts": 8.3, "grid.spec.ts": 1.9, "map.spec.ts": 72.0}
    plans = [e2eparts.plan(f"{i}/2", LISTING, durations, parallel) for i in (1, 2)]
    assert ["map.spec.ts"] in plans


def test_every_test_plays_once_whatever_the_durations_and_the_count() -> None:
    known = e2eparts.measure(LOG, parallel)
    for durations in ({}, known, {"gone.spec.ts": 99.0}):
        for count in (1, 2, 3, 5, 9):
            plans = [
                e2eparts.plan(f"{i}/{count}", LISTING, durations, parallel)
                for i in range(1, count + 1)
            ]
            everything = sorted((file, title) for file, title, _ in e2eparts.listed(LISTING))
            assert sorted(played(plans)) == everything


def test_a_file_the_durations_do_not_know_plays_for_the_mean_of_the_known_ones() -> None:
    durations = {"admin.spec.ts": 10.0, "grid.spec.ts": 30.0}
    first, second = (e2eparts.plan(f"{i}/2", LISTING, durations, parallel) for i in (1, 2))
    assert "map.spec.ts" in first + second
    # the unknown file weighs 20 s: it goes with admin.spec.ts (10 s), not grid.spec.ts (30 s)
    with_map = next(part for part in (first, second) if "map.spec.ts" in part)
    assert "grid.spec.ts" not in with_map


def test_without_any_duration_the_units_are_still_spread() -> None:
    plans = [e2eparts.plan(f"{i}/2", LISTING, {}, parallel) for i in (1, 2)]
    assert all(plans)


@pytest.mark.parametrize("shard", ["", "1", "0/5", "6/5", "a/b", "1/5/5"])
def test_a_part_is_i_over_n(shard: str) -> None:
    with pytest.raises(ValueError, match="i/N"):
        e2eparts.parse_shard(shard)


def test_the_durations_are_written_one_unit_a_line_and_read_back(tmp_path: Path) -> None:
    target = tmp_path / "durations.json"
    e2eparts.write({"a.spec.ts": 1.5, f"b.spec.ts{SEPARATOR}t": 2.0}, target)
    assert target.read_text(encoding="utf-8").count("\n") == 4
    assert e2eparts.read(target) == {"a.spec.ts": 1.5, f"b.spec.ts{SEPARATOR}t": 2.0}


def test_the_files_played_test_by_test_are_the_ones_that_say_so(tmp_path: Path) -> None:
    (tmp_path / "e2e").mkdir()
    (tmp_path / "e2e" / "a.spec.ts").write_text('test.describe.configure({ mode: "parallel" });')
    (tmp_path / "e2e" / "b.spec.ts").write_text('test.describe.configure({ mode: "serial" });')
    assert e2eparts.is_parallel("a.spec.ts", tmp_path)
    assert not e2eparts.is_parallel("b.spec.ts", tmp_path)


def test_the_versioned_durations_are_those_of_the_paths_of_the_repository() -> None:
    durations = json.loads(e2eparts.DURATIONS.read_text(encoding="utf-8"))
    assert durations
    assert all(seconds >= 0 for seconds in durations.values())
    assert not [unit for unit in durations if unit.startswith(("e2e/", "service/"))]
