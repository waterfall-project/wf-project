# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision of the witness of volume, PRJ-001, written a table at a time (US-2240/L2).

The current revision 102 is abandoned, and a revision opened from the last marked one, the 101: a
thousand tasks and five thousand lines, copied each by one statement since US-2240/L2. The copy
holds what the sentence of WF-REV-0010-A says: the same tasks and the same lines, row for row and
table for table (WF-DAT-0010), under their lineage; and, its year moved on, the rate the 101 kept
for each category projected by the rate of inflation of the project. The 101 was marked once
PRJ-001 was In progress: its lines give their figures as the remaining to commit before the review
(EP-09); the reference is the offer 100, whose lines give the budgeted amounts by lineage.
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102

from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.projects.interface import (
    ContributorFilters,
    ContributorSort,
    Viewer,
    list_contributors,
)
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import (
    RevisionToAbandon,
    abandon_revision,
    create_revision,
    read_revision,
)
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-REV-0010-A")

# The opening at the year of the 101, then a year later: its rates projected.
SAME_YEAR = datetime(2026, 6, 3, 14, 5, tzinfo=UTC)
NEXT_YEAR = datetime(2027, 1, 11, 9, 0, tzinfo=UTC)
CENT = Decimal("0.01")
# What a task keeps of its source, but its dates, which the opening dates again (WF-PLA-0160).
TASK_KEPT = (
    "kind",
    "label",
    "description",
    "scheduling_mode",
    "duration_value",
    "duration_unit",
    "progress",
    "external_id",
    "work_package_id",
    "order_item_id",
)
# What a line keeps of its source, but its amounts, which the copy of the rates prices again.
LINE_KEPT = (
    "kind",
    "label",
    "cost_category_id",
    "resource_role_id",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject_id",
    "remaining_reason",
    "reestimated_at",
)
PREVIOUS = ("quantity", "hours", "unit_disbursement", "reestimated_amount")


def _opened(database: Database, at: datetime) -> UUID:
    """Abandon the current revision of PRJ-001, open one at ``at`` as its manager; give it."""
    with logging_context(correlation_id="revision-copy"), database.transaction() as session:
        manager = (
            list_contributors(
                session,
                PRJ_001,
                ContributorFilters(kinds=frozenset({"project_manager"})),
                ContributorSort(),
            )
            .items[0]
            .user_id
        )
        viewer = Viewer(manager, ())
        current = read_revision(session, PRJ_001, REVISION_102, viewer)
        abandon_revision(
            session,
            PRJ_001,
            RevisionToAbandon(REVISION_102, current.lock_version),
            Act(manager, at),
            viewer,
        )
        session.flush()
        return create_revision(session, PRJ_001, Act(manager, at), viewer).revision_id


def _nodes(session: Session, revision_id: UUID) -> dict[UUID, Node]:
    """Give the nodes of a revision of PRJ-001, by their lineage."""
    return {
        node.lineage_id: node
        for node in session.scalars(
            select(Node).where(Node.project_id == PRJ_001, Node.revision_id == revision_id)
        )
    }


def _tasks(session: Session, nodes: dict[UUID, Node]) -> dict[UUID, Task]:
    """Give the tasks of the nodes named, by the lineage of their node."""
    lineage = {node.id: each for each, node in nodes.items()}
    rows = session.scalars(
        select(Task).where(Task.project_id == PRJ_001, Task.node_id.in_(list(lineage)))
    )
    return {lineage[row.node_id]: row for row in rows}


def _lines(session: Session, nodes: dict[UUID, Node]) -> dict[UUID, EstimateLine]:
    """Give the lines of the nodes named, by the lineage of their node."""
    lineage = {node.id: each for each, node in nodes.items()}
    rows = session.scalars(
        select(EstimateLine).where(
            EstimateLine.project_id == PRJ_001, EstimateLine.node_id.in_(list(lineage))
        )
    )
    return {lineage[row.node_id]: row for row in rows}


def _links(session: Session, revision_id: UUID) -> set[tuple[object, ...]]:
    """Give the links of a revision, each by the lineages of its two tasks and what it says."""
    nodes = {
        node.id: node.lineage_id
        for node in session.scalars(
            select(Node).where(Node.project_id == PRJ_001, Node.revision_id == revision_id)
        )
    }
    return {
        (
            nodes[link.predecessor_id],
            nodes[link.successor_id],
            link.link_type,
            link.lag_value,
            link.lag_unit,
            link.in_conflict,
        )
        for link in session.scalars(
            select(TaskLink).where(
                TaskLink.project_id == PRJ_001, TaskLink.revision_id == revision_id
            )
        )
    }


def test_a_revision_opened_on_prj_001_bears_the_same_tasks_and_lines_as_its_marked_source(
    witness: Database,
) -> None:
    # The volumes of PRJ-001 (§4.6.2): every row of the 101 copied once, none lost, none doubled.
    opened = _opened(witness, SAME_YEAR)
    with witness.transaction() as session:
        source, copy = _nodes(session, REVISION_101), _nodes(session, opened)
        assert len(copy) == len(source) > 5000
        assert (
            len(
                {node.id for node in copy.values()}.intersection(
                    node.id for node in source.values()
                )
            )
            == 0
        )
        for lineage, node in copy.items():
            was = source[lineage]
            assert (node.kind, node.rank, node.lock_version) == (was.kind, was.rank, 1)
            parent = (
                None if was.parent_id is None else session.get_one(Node, (PRJ_001, was.parent_id))
            )
            assert (node.parent_id is None) == (parent is None)
            if parent is not None:
                assert node.parent_id == copy[parent.lineage_id].id
        tasks = _tasks(session, source), _tasks(session, copy)
        assert len(tasks[1]) == len(tasks[0]) > 900
        for lineage, task in tasks[1].items():
            kept = [getattr(tasks[0][lineage], name) for name in TASK_KEPT]
            assert [getattr(task, name) for name in TASK_KEPT] == kept
        assert _links(session, opened) == _links(session, REVISION_101)
        lines = _lines(session, source), _lines(session, copy)
        assert len(lines[1]) == len(lines[0]) > 4900
        reference = _lines(session, _nodes(session, REVISION_100))
        for lineage, line in lines[1].items():
            was = lines[0][lineage]
            assert [getattr(line, name) for name in LINE_KEPT] == [
                getattr(was, name) for name in LINE_KEPT
            ]
            assert line.lock_version == 1
            # The 101 is a review: its figures are the remaining to commit before it (EP-09).
            assert [getattr(line, f"previous_{name}") for name in PREVIOUS] == [
                getattr(was, name) for name in PREVIOUS
            ]
            held = reference.get(lineage)
            budgeted = (
                Decimal("0.00")
                if held is None
                else held.reestimated_amount
                if held.budgeted_amount is None
                else held.budgeted_amount
            )
            assert line.budgeted_amount == budgeted


def test_a_revision_opened_on_prj_001_a_year_later_projects_the_rates_its_source_kept(
    witness: Database,
) -> None:
    # The update of the rates is not accepted: each rate the 101 kept, projected one year by the
    # rate of inflation of the project, rounded to the cent.
    opened = _opened(witness, NEXT_YEAR)
    with witness.transaction() as session:
        inflation = session.scalars(
            select(Project.inflation_rate).where(Project.id == PRJ_001)
        ).one()

        def rates(revision_id: UUID) -> dict[UUID, tuple[Decimal, str]]:
            return {
                rate.cost_category_id: (rate.amount, rate.origin)
                for rate in session.scalars(
                    select(RevisionRate).where(
                        RevisionRate.project_id == PRJ_001, RevisionRate.revision_id == revision_id
                    )
                )
            }

        kept = rates(REVISION_101)
        assert kept
        assert rates(opened) == {
            category: (
                (amount * (1 + inflation)).quantize(CENT, rounding=ROUND_HALF_UP),
                "projected",
            )
            for category, (amount, _) in kept.items()
        }
        counted = {
            entity.__name__: session.scalar(
                select(func.count())
                .select_from(entity)
                .where(entity.project_id == PRJ_001, entity.revision_id == opened)
            )
            for entity in (Node, TaskLink)
        }
        assert counted == {
            entity.__name__: session.scalar(
                select(func.count())
                .select_from(entity)
                .where(entity.project_id == PRJ_001, entity.revision_id == REVISION_101)
            )
            for entity in (Node, TaskLink)
        }
