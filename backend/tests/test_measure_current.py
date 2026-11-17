# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the comparison of the current revision (EP-27, US-2390): its parts, its counts.

``make measure-core`` compares the current revision of PRJ-001 with the marked one it copies, whole
and on its tasks, split into its readings, its union and its body, and counts the nodes that differ
between them (``ONLY=current``): the figures #3168 asks to instruct its option 3, read in the report
of WF-QUA-0060. The tool is no requirement's, and its tests cite none: they hold its arithmetic,
and, on the witness of the tests, its promise to leave nothing written.
"""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from measure.__main__ import main
from measure.current import differing_of, measure_current, split_of
from measure.target import locate
from waterfall.core.planning.tables import StructureReading
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from waterfall.platform.database import Database


def test_the_union_is_what_the_comparison_takes_beyond_its_readings() -> None:
    split = split_of(0.6, 0.9, 0.1)

    assert split.union == pytest.approx(0.3)
    assert split.total == pytest.approx(1.0)
    facts = split.facts()
    assert facts["readings_ms"] == pytest.approx(600.0)
    assert facts["readings_share"] == pytest.approx(0.6)
    assert facts["union_share"] == pytest.approx(0.3)
    assert facts["body_share"] == pytest.approx(0.1)
    assert facts["union_and_body_share"] == pytest.approx(0.4)


def test_a_union_timed_under_its_readings_counts_nought() -> None:
    split = split_of(0.5, 0.45, 0.05)

    assert split.union == 0.0
    assert split.facts()["union_share"] == 0.0


def test_the_nodes_are_counted_by_kind_and_by_mark_the_redated_and_the_summaries_apart() -> None:
    items: list[dict[str, object]] = [
        {"kind": "task", "difference": "unchanged", "changes": []},
        {"kind": "task", "difference": "modified", "changes": ["dates"]},
        {"kind": "task", "difference": "modified", "changes": ["dates", "duration"]},
        {"kind": "task", "difference": "modified", "changes": []},
        {"kind": "task", "difference": "added", "changes": []},
        {"kind": "estimate_line", "difference": "removed", "changes": []},
        {"kind": "estimate_line", "difference": "unchanged", "changes": []},
    ]

    line, task = differing_of(items)

    assert line.row() == {
        "kind": "estimate_line",
        "nodes": 2,
        "differing": 1,
        "added": 0,
        "removed": 1,
        "modified": 0,
        "dates_only": 0,
        "content_only": 0,
    }
    assert (task.nodes, task.differing, task.added, task.modified) == (5, 4, 1, 3)
    assert (task.dated, task.content) == (1, 1)


def test_the_part_of_the_current_revision_is_one_the_parser_offers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["--only", "nothing"])

    assert "kept, current)" in capsys.readouterr().err


def _kept(database: Database) -> int:
    with database.transaction() as session:
        return int(session.scalar(select(func.count()).select_from(StructureReading)) or 0)


def test_the_comparison_of_the_current_revision_measured_leaves_nothing_written(
    witness: Database,
) -> None:
    target = locate(witness)
    before = _kept(witness)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        whole, tasks, differing = measure_current(witness, target, 1)

    # The reading kept of the base the first comparison makes is rolled back with the rest.
    assert _kept(witness) == before == 0
    assert whole.summary is not None
    assert tasks.summary is not None
    assert float(whole.facts["readings_ms"]) > 0
    assert float(whole.facts["body_ms"]) > 0
    assert 0 < float(tasks.facts["tasks"]) < float(whole.facts["nodes"])
    assert differing.facts["nodes"] == whole.facts["nodes"]
    assert [each["kind"] for each in differing.rows] == ["estimate_line", "task"]
    assert 0 <= float(differing.facts["differing_share"]) <= 1
