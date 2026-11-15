# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision of PRJ-001 sends a handful of statements, not one by row (#3526).

US-2240/L2 brought the copy of the last marked revision from 3 621 statements to 85: an
``INSERT ... SELECT`` by table. Nothing kept it so; this test counts the statements of the copy
alone and bounds them widely, so that a copy row by row, a statement for each of the thousand
tasks and five thousand lines, fails it.
"""

from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import event
from test_revision_copy_witness import SAME_YEAR
from test_witness_projects import PRJ_001, REVISION_102

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
    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-REV-0010-A")

# The statements the copy may send, whatever the volume. They depend on the number of tables the
# copy visits (85 today, an ``INSERT ... SELECT`` and its few reads by table), never on the rows
# of PRJ-001: a copy row by row sends 3 621 and more. 200 leaves room for tables added by later
# epics, and stays far under what a row-by-row copy sends.
COPY_STATEMENTS_BOUND = 200


def test_the_copy_of_a_revision_of_prj_001_sends_fewer_statements_than_a_bound_of_tables(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        create_revision(session, PRJ_001, act, viewer)

    assert 0 < len(sent) < COPY_STATEMENTS_BOUND, len(sent)
