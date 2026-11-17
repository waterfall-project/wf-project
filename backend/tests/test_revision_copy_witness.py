# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision of the witness of volume, PRJ-001, written a table at a time (US-2240/L2).

The current revision 102 is abandoned, and a revision opened from the last marked one, the 101: a
thousand tasks and five thousand lines, copied each by one statement since US-2240/L2. The copy
holds what the sentence of WF-REV-0010-A says: the same tasks and the same lines, row for row and
table for table (WF-DAT-0010), under their lineage; and, its year moved on, the rate the 101 kept
for each category projected by the rate of inflation of the project, its lines priced again at it,
each to the amount the pricing of a line computes (US-2240/L6, #3535). The 101 was marked once
PRJ-001 was In progress: its lines give their figures as the remaining to commit before the review
(EP-09); the reference is the offer 100, whose lines give the budgeted amounts by lineage.
"""

import re
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import event, func, inspect, select
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102

from waterfall.core.estimate.keeping import reprice_revision
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
# What a copy does not take as it is, whatever the year. Of a task, its keys: the node and the
# structure are the copy's own.
TASK_OWN = ("node_id", "structure_id")
# Of a line, its node; its stamps (``created_*``, ``updated_*``), not compared; and what the
# opening sets by its own rule, proved apart below: the lock version, the budgeted amount, the
# previous figures.
LINE_OWN = (
    "node_id",
    "lock_version",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
    "budgeted_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)
PREVIOUS = ("quantity", "hours", "unit_disbursement", "reestimated_amount")
# A statement writing the lines, as sent, newlines kept (one ends a ``--`` comment). The comments
# go first (``_uncommented``), then an ``UPDATE`` of ``estimate_line`` is sought anywhere in what is
# left: at the head, behind a ``WITH`` or after a ``;``. A quoted literal or name is kept whole, so
# that a ``--`` or a ``/*`` in it opens no comment (#3655); one naming such an ``UPDATE`` counts
# too: too wide, not too narrow. An ``INSERT … ON CONFLICT DO UPDATE`` is an insertion, the copy
# itself, and a ``FOR UPDATE`` a lock: neither counts.
QUOTED = re.compile(r"""'(?:[^']|'')*'? | "(?:[^"]|"")*"?""", re.VERBOSE)
NESTING = re.compile(r"/\* | \*/", re.VERBOSE)
LINE_UPDATE = re.compile(
    r"""
    \bupdate\s+              # the verb, then its target
    (?:only\s+)?              # PostgreSQL: not the tables inheriting from it
    (?:"?\w+"?\.)?           # the schema, quoted or not, if the name is qualified
    "?estimate_line"?        # the table, quoted or not...
    (?![\w"])                # ... and not a longer name starting with it
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _comment_end(statement: str, at: int) -> int:
    """Give where the ``/*`` comment opened at ``at`` ends: its own ``*/``, nested ones counted.

    PostgreSQL nests them (#3656); one never closed runs to the end of the statement, which
    PostgreSQL refuses, writing nothing.
    """
    depth = 0
    for mark in NESTING.finditer(statement, at):
        depth += 1 if mark.group() == "/*" else -1
        if depth == 0:
            return mark.end()
    return len(statement)


def _uncommented(statement: str) -> str:
    """Give a statement its comments blanked, its quoted literals and names kept as they are.

    Not read, as SQLAlchemy sends none: the dollar quotes (``$$…$$``) and the backslash escapes of
    an ``E'…'``, a quote they hide ending the literal early.
    """
    kept: list[str] = []
    at = 0
    while at < len(statement):
        if statement.startswith("--", at):
            end = statement.find("\n", at)
            at = len(statement) if end < 0 else end
            kept.append(" ")
        elif statement.startswith("/*", at):
            at = _comment_end(statement, at)
            kept.append(" ")
        elif (quoted := QUOTED.match(statement, at)) is not None:
            kept.append(quoted.group())
            at = quoted.end()
        else:
            kept.append(statement[at])
            at += 1
    return "".join(kept)


def _writes_lines(statement: str) -> bool:
    """Tell whether a statement, comments aside, updates ``estimate_line``."""
    return LINE_UPDATE.search(_uncommented(statement)) is not None


@pytest.mark.parametrize(
    ("statement", "writes"),
    [
        ("UPDATE estimate_line SET quantity = 1", True),
        ('UPDATE "estimate_line" SET quantity = 1', True),
        ("update public.estimate_line set quantity = 1", True),
        ('UPDATE "public"."estimate_line" SET quantity = 1', True),
        ("/* c */ UPDATE estimate_line SET quantity = 1", True),
        ("-- c\nUPDATE estimate_line SET quantity = 1", True),
        ("UPDATE ONLY estimate_line SET quantity = 1", True),
        ("WITH x AS (SELECT 1) UPDATE estimate_line SET quantity = 1", True),
        ("SELECT 1; UPDATE estimate_line SET quantity = 1", True),
        ("/* UPDATE estimate_line */ SELECT 1", False),
        ("UPDATE estimate_line_x SET quantity = 1", False),
        ("UPDATE other SET estimate_line = 1", False),
        ("SELECT quantity FROM estimate_line", False),
        ("SELECT 1 -- UPDATE estimate_line", False),
        # #3655: a literal holding a comment's mark opens none, nor does a doubled quote end it.
        ("SELECT '--'; UPDATE estimate_line SET q=1", True),
        ("SELECT 'a/*'; UPDATE estimate_line SET q=1 -- */", True),
        ("SELECT 'it''s --'; UPDATE estimate_line SET q=1", True),
        ('SELECT 1 AS "a--b"; UPDATE estimate_line SET q=1', True),
        ("SELECT quantity FROM estimate_line FOR UPDATE", False),
        ("INSERT INTO estimate_line VALUES (1) ON CONFLICT DO UPDATE SET q=1", False),
        # #3656: comments nest, and one never closed runs to the end.
        ("/* a /* b */ UPDATE estimate_line SET q=1 */ SELECT 1", False),
        ("/* a /* b */ c */ UPDATE estimate_line SET q=1", True),
        ("SELECT 1 /* UPDATE estimate_line SET q=1", False),
    ],
)
def test_the_witness_of_the_copy_detects_every_update_of_the_lines_and_only_them(
    statement: str, writes: bool
) -> None:
    # The detector of the test below: not too narrow (#3603), nor too wide.
    assert _writes_lines(statement) is writes


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


def _columns(row: Task | EstimateLine, own: tuple[str, ...]) -> dict[str, object]:
    """Give every column of a row but those ``own``: a column added later is compared too."""
    return {
        column.key: getattr(row, column.key)
        for column in inspect(type(row)).column_attrs
        if column.key not in own
    }


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


def _rates(session: Session, revision_id: UUID) -> dict[UUID, tuple[Decimal, str]]:
    """Give the rates a revision keeps, by cost category: their amount and their origin."""
    return {
        rate.cost_category_id: (rate.amount, rate.origin)
        for rate in session.scalars(
            select(RevisionRate).where(
                RevisionRate.project_id == PRJ_001, RevisionRate.revision_id == revision_id
            )
        )
    }


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
            assert _columns(task, TASK_OWN) == _columns(tasks[0][lineage], TASK_OWN)
        assert _links(session, opened) == _links(session, REVISION_101)
        lines = _lines(session, source), _lines(session, copy)
        assert len(lines[1]) == len(lines[0]) > 4900
        reference = _lines(session, _nodes(session, REVISION_100))
        for lineage, line in lines[1].items():
            was = lines[0][lineage]
            # At the year of the source, its amounts as they are: the rates are the same.
            assert _columns(line, LINE_OWN) == _columns(was, LINE_OWN)
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
        # And at the year of the source, the rates it kept: the same, to the cent and the origin.
        assert _rates(session, opened) == _rates(session, REVISION_101) != {}


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

        kept = _rates(session, REVISION_101)
        assert kept
        assert _rates(session, opened) == {
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

    # Its lines priced again at the rates projected, by set (#3535): each holds the amount the
    # pricing of a line computes — priced once more, none moves —, and the copy moved them on.
    with witness.transaction() as session:
        session.expire_all()
        engine = session.get_bind()
        sent: list[str] = []

        def heard(*arguments: Any) -> None:
            sent.append(str(arguments[2]))

        event.listen(engine, "before_cursor_execute", heard)
        try:
            reprice_revision(session, (PRJ_001, opened), NEXT_YEAR)
            session.flush()
        finally:
            event.remove(engine, "before_cursor_execute", heard)
        # The listener heard the pass (its reads of the lines), and none of it wrote a line.
        assert any("estimate_line" in each.lower() for each in sent)
        writes = [each for each in sent if _writes_lines(each)]
        assert writes == []
        source = _lines(session, _nodes(session, REVISION_101))
        copied = _lines(session, _nodes(session, opened))
        assert copied.keys() == source.keys()
        assert sum(line.base_amount for line in copied.values()) > sum(
            line.base_amount for line in source.values()
        )
        # Each amount computed apart: a labour line, its quantity x hours x the rate projected; any
        # other, its quantity x unit disbursement, which no rate moves.
        projected = _rates(session, opened)
        labour = other = 0
        for lineage, line in copied.items():
            if line.resource_role_id is None:
                assert line.unit_disbursement is not None
                expected = (line.quantity * line.unit_disbursement).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
                other += 1
            else:
                assert line.hours is not None
                assert line.cost_category_id in projected, (
                    f"line {lineage}: its category has no rate in the revision opened"
                )
                expected = (
                    line.quantity * line.hours * projected[line.cost_category_id][0]
                ).quantize(CENT, rounding=ROUND_HALF_UP)
                labour += 1
            assert line.base_amount == expected
        assert labour > 0
        assert other > 0
