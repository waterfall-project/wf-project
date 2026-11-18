# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the comparison of the current revision (EP-27, US-2390): its parts, its counts.

``make measure-core`` compares the current revision of PRJ-001 with the marked one it copies, whole
from the rows and from what is kept, and on its tasks, split into its readings, its union and its
body, and counts the nodes that differ between them (``ONLY=current``): the figures #3168 asks to
instruct its option 3, read in the report of WF-QUA-0060. The tool is no requirement's, and its
tests cite none: they hold its arithmetic, and, on the witness of the tests, its promise to leave
nothing written.
"""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import measure.current
from measure.__main__ import PARTS
from measure.current import differing_of, measure_current, split_of
from measure.target import locate
from waterfall.core.history.tables import UndoEntry
from waterfall.core.planning.tables import Node, StructureReading, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from waterfall.platform.database import Database

_COUNTED = (StructureReading, Node, Task, TaskLink, CostStructure, Revision, UndoEntry)


def test_the_union_is_what_the_comparison_takes_beyond_its_readings() -> None:
    split = split_of(0.6, 0.9, 0.1)

    assert split.union == pytest.approx(0.3)
    assert split.total == pytest.approx(1.0)
    facts = split.facts()
    assert facts["total_ms"] == pytest.approx(1000.0)
    assert facts["readings_ms"] == pytest.approx(600.0)
    assert facts["readings_share"] == pytest.approx(0.6)
    assert facts["union_share"] == pytest.approx(0.3)
    assert facts["body_share"] == pytest.approx(0.1)
    assert facts["union_and_body_share"] == pytest.approx(0.4)
    assert facts["union_clamped"] is False


def test_a_union_timed_under_its_readings_is_said_and_the_shares_keep_their_total() -> None:
    split = split_of(0.5, 0.45, 0.05)

    assert split.union == 0.0
    assert split.clamped
    facts = split.facts()
    assert facts["union_clamped"] is True
    # The readings as timed, but the total is the comparison and its body, which the shares share.
    assert facts["readings_ms"] == pytest.approx(500.0)
    assert facts["total_ms"] == pytest.approx(500.0)
    assert facts["union_share"] == 0.0
    shares = ("readings_share", "union_share", "body_share")
    assert sum(float(facts[each]) for each in shares) == pytest.approx(1.0)


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
        "other_changes": 0,
    }
    assert (task.nodes, task.differing, task.added, task.modified) == (5, 4, 1, 3)
    # Each modified one falls in one column: the dates alone, what is under it, or another change.
    assert (task.dated, task.content, task.other) == (1, 1, 1)


def test_the_part_of_the_current_revision_is_one_the_parser_offers() -> None:
    assert "current" in PARTS


def _counts(database: Database) -> dict[str, int]:
    with database.transaction() as session:
        return {
            table.__tablename__: int(session.scalar(select(func.count()).select_from(table)) or 0)
            for table in _COUNTED
        }


def test_the_comparison_of_the_current_revision_measured_leaves_nothing_written(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = locate(witness)
    before = _counts(witness)
    kept_in_session: list[int] = []

    class Observed(Session):
        """The session of the measure, which counts the readings kept before it rolls back."""

        def rollback(self) -> None:
            kept_in_session.append(
                int(self.scalar(select(func.count()).select_from(StructureReading)) or 0)
            )
            super().rollback()

    monkeypatch.setattr(measure.current, "Session", Observed)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        rows, kept, tasks, differing = measure_current(witness, target, 2)

    # The reading kept of the base the first comparison makes is written in the transaction, and
    # rolled back with the rest: no table the comparison may write keeps a row of it.
    assert before[StructureReading.__tablename__] == 0
    assert kept_in_session == [1]
    assert _counts(witness) == before
    for each in (rows, kept, tasks):
        assert each.summary is not None
        assert each.summary.runs == 2
        assert float(each.facts["readings_ms"]) > 0
        assert float(each.facts["body_ms"]) > 0
        assert "runs_union_negative" in each.facts
    # The whole from the rows, the quantity of the threshold of #3168, has the parts of the other.
    assert rows.facts.keys() == kept.facts.keys() | {"union_and_body_under_threshold"}
    assert "union_and_body_under_threshold" in tasks.facts
    assert 0 < float(tasks.facts["tasks"]) < float(rows.facts["nodes"])
    assert differing.facts["nodes"] == rows.facts["nodes"] == kept.facts["nodes"]
    assert [each["kind"] for each in differing.rows] == ["estimate_line", "task"]
    # The current revision of the witness differs from the marked one it copies in some nodes, not
    # all: a comparison of a revision with itself, or with one it does not copy, fails here.
    assert 0 < int(differing.facts["differing"]) < int(differing.facts["nodes"])
