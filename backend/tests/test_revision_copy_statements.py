# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision of PRJ-001 sends a handful of statements, not one by row (#3526).

US-2240/L2 brought the copy of the last marked revision to an ``INSERT ... SELECT`` by table, and
US-2240/L6 the pricing again of its lines, when the revision opened changes year, to a statement
by set (#3535). Nothing kept it so; this test counts the statements of the copy alone, within the
year of the source and a year later, and bounds them widely, so that a copy with a statement for
each row of the tasks and lines of PRJ-001 fails it.

What the guard covers is bounded: it counts statements, not rows. A grouped ORM insertion
(``add_all``, insertmanyvalues) could stay under the bound; the guard is against one statement by
row.
"""

import re
from collections import Counter
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import event, func, select
from test_revision_copy_witness import NEXT_YEAR, SAME_YEAR
from test_witness_projects import PRJ_001, REVISION_101, REVISION_102

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.interface import (
    ContributorFilters,
    ContributorSort,
    Viewer,
    list_contributors,
)
from waterfall.core.revisions.interface import (
    RevisionToAbandon,
    abandon_revision,
    create_revision,
    read_revision,
    revisions,
)
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from datetime import datetime

    from waterfall.platform.database import Database

# The statements the copy may send, whatever the volume (#3526). They depend on the number of
# tables the copy visits, an ``INSERT ... SELECT`` and its few reads by table, and on the number of
# structures it redates, a few reads by structure, never on the rows of PRJ-001, nor on its year: a
# revision opened a year later prices its lines again by a statement for the set (#3535), not one
# by line. Since EP-08 the 101 of the witness holds six structures the copy takes up — the main
# one, the amendment 2 and its base, the three own estimates — where it held one (US-2650/L1): 300
# leaves a margin for tables added by later epics, and stays far from a copy by row. Since
# US-3070/L3 each own estimate is born whole with its base (EP-30): the 101 holds nine structures,
# and the copy sends some 420 statements within the year, 450 a year later, some 50 a structure,
# none by row. 500 is the declared deviation of US-3070/L3: the pruning at the marking, US-3070/L4
# (#4587), takes the bases of the 101 away and brings the bound back to 300.
COPY_STATEMENTS_BOUND = 500
# The volume of the source the bound is read against: a thinner witness would let a copy by row
# pass under 200 (PRJ-001: some 1 000 tasks, 5 000 lines).
TASKS_FLOOR = 900
LINES_FLOOR = 4_500
# What the message of a failure groups the statements by: their verb, and the table they write or
# read first, that follows ``INTO``, ``UPDATE`` or ``FROM`` (#3538).
TABLE = re.compile(r"\b(?:INTO|UPDATE|FROM)\s+(\w+)")


def _grouped(statement: str) -> str:
    """Name a statement by its verb and the first table it writes or reads."""
    table = TABLE.search(statement)
    verb = statement.split(maxsplit=1)[0] if statement.strip() else ""
    return verb if table is None else f"{verb} {table.group(1)}"


@pytest.mark.parametrize("at", [SAME_YEAR, NEXT_YEAR], ids=["same_year", "next_year"])
def test_the_copy_of_a_revision_sends_fewer_statements_than_its_bound(
    witness: Database, monkeypatch: pytest.MonkeyPatch, at: datetime
) -> None:
    # A criterion of the story's own, which reprises no Vérif: it cites no requirement.
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    copy = revisions.copy_revision

    def counted(*arguments: Any, **keywords: Any) -> None:
        # Only the copy: the opening, its reads and its writes around it are not counted.
        engine = arguments[0].get_bind()
        event.listen(engine, "before_cursor_execute", heard)
        try:
            copy(*arguments, **keywords)
        finally:
            event.remove(engine, "before_cursor_execute", heard)

    monkeypatch.setattr(revisions, "copy_revision", counted)
    with logging_context(correlation_id="revision-copy"), witness.transaction() as session:
        filters = ContributorFilters(kinds=frozenset({"project_manager"}))
        manager = list_contributors(session, PRJ_001, filters, ContributorSort()).items[0].user_id
        viewer = Viewer(manager, ())
        current = read_revision(session, PRJ_001, REVISION_102, viewer)
        act = Act(manager, at)
        abandon_revision(
            session, PRJ_001, RevisionToAbandon(REVISION_102, current.lock_version), act, viewer
        )
        session.flush()
        # Joined on the project too, the key of the partitions: joined on the node alone, the rows
        # laid again unanalysed, PostgreSQL scanned every partition for each node, a minute or more.
        in_source = (Node.project_id == PRJ_001, Node.revision_id == REVISION_101)
        tasks = session.scalar(
            select(func.count())
            .select_from(Task)
            .join(Node, (Node.project_id == Task.project_id) & (Node.id == Task.node_id))
            .where(*in_source)
        )
        lines = session.scalar(
            select(func.count())
            .select_from(EstimateLine)
            .join(
                Node,
                (Node.project_id == EstimateLine.project_id) & (Node.id == EstimateLine.node_id),
            )
            .where(*in_source)
        )
        assert tasks is not None
        assert lines is not None
        assert tasks >= TASKS_FLOOR, tasks
        assert lines >= LINES_FLOOR, lines
        create_revision(session, PRJ_001, act, viewer)

    grouped = Counter(_grouped(each) for each in sent).most_common(5)
    assert 0 < len(sent) < COPY_STATEMENTS_BOUND, (len(sent), grouped)
