# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision of PRJ-001 sends a handful of statements, not one by row (#3526).

US-2240/L2 brought the copy of the last marked revision to an ``INSERT ... SELECT`` by table.
Nothing kept it so; this test counts the statements of the copy alone and bounds them widely, so
that a copy with a statement for each row of the thousand tasks and five thousand lines fails it.

What the guard covers is bounded: it counts statements, not rows. A grouped ORM insertion
(``add_all``, insertmanyvalues) could stay under the bound; the guard is against one statement by
row. It guards the copy within the same year only: a revision that changes year reprices its
lines one by one, a finding opened apart (#3535).
"""

from collections import Counter
from typing import TYPE_CHECKING, Any

from sqlalchemy import event, func, select
from test_revision_copy_witness import SAME_YEAR
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
    import pytest

    from waterfall.platform.database import Database

# The statements the copy may send, whatever the volume (#3526). They depend on the number of
# tables the copy visits, an ``INSERT ... SELECT`` and its few reads by table, never on the rows
# of PRJ-001. 200 leaves a wide margin for tables added by later epics, and stays far from a copy
# by row.
COPY_STATEMENTS_BOUND = 200
# The volume of the source the bound is read against: a thinner witness would let a copy by row
# pass under 200 (PRJ-001: some 1 000 tasks, 5 000 lines).
TASKS_FLOOR = 900
LINES_FLOOR = 4_500


def test_the_copy_of_a_revision_sends_fewer_statements_than_its_bound(
    witness: Database, monkeypatch: pytest.MonkeyPatch
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
        act = Act(manager, SAME_YEAR)
        abandon_revision(
            session, PRJ_001, RevisionToAbandon(REVISION_102, current.lock_version), act, viewer
        )
        session.flush()
        in_source = (Node.project_id == PRJ_001, Node.revision_id == REVISION_101)
        tasks = session.scalar(
            select(func.count())
            .select_from(Task)
            .join(Node, Node.id == Task.node_id)
            .where(*in_source)
        )
        lines = session.scalar(
            select(func.count())
            .select_from(EstimateLine)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(*in_source)
        )
        assert tasks is not None
        assert lines is not None
        assert tasks >= TASKS_FLOOR, tasks
        assert lines >= LINES_FLOOR, lines
        create_revision(session, PRJ_001, act, viewer)

    beginnings = Counter(" ".join(each.split()[:3]) for each in sent).most_common(5)
    assert 0 < len(sent) < COPY_STATEMENTS_BOUND, (len(sent), beginnings)
