# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The consultation of the journal at its scale: a page on one snapshot, the facets by indexes.

The total of a page and its lines are read on one snapshot, two sessions meeting between the two
readings (#928); the facets, which name each author and each project of the journal, do not read
the journal whole, tried on the set of reference loaded (US-2950) and a journal grown to its
volumes (#934). Both are the criteria of US-2980 that belong to it.
"""

from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.dialects import postgresql
from test_audit_consultation import CLAIRE, JOURNAL, Written, at, write
from test_witness_reference import UNEXTENDED, settings

from waterfall.platform.audit import AuditEntry
from waterfall.platform.audit_consultation import (
    AuditFilters,
    AuditSort,
    journal_actors,
    journal_projects,
    latest_first,
    list_entries,
)
from waterfall.witness import reference_load

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from waterfall.platform.database import Database

pytestmark = pytest.mark.story("US-2980")

# The inscription a second session writes between the two readings of a page: at the latest.
LATE = Written(at(20), CLAIRE, "user_deactivate", "user", "Zoé Arnaud", "req-late")
# The projects the set is loaded with, and how many times its journal is copied to reach volumes
# the planner reads by its indexes: a journal of some sixty thousand inscriptions.
PROJECTS = 12
COPIES = 100
# Out of its dates, the inscription copied is the one it copies, a minute apart from the others.
GROW = text(
    "INSERT INTO audit_entry (id, occurred_at, actor_user_id, actor_display_name, action, "
    "object_kind, object_id, object_label, object_revision_id, object_revision_label, project_id, "
    "project_code, project_label, params, correlation_id) "
    "SELECT gen_random_uuid(), occurred_at - make_interval(mins => copy), actor_user_id, "
    "actor_display_name, action, object_kind, object_id, object_label, object_revision_id, "
    "object_revision_label, project_id, project_code, project_label, params, correlation_id "
    "FROM audit_entry CROSS JOIN generate_series(1, :copies) AS copy"
)
# The composite indexes of each facet, which a probe of the latest inscription of one value reads.
COMPOSITE = {
    AuditEntry.actor_user_id: "ix_audit_entry_actor_latest",
    AuditEntry.project_id: "ix_audit_entry_project_latest",
}


def read_between(database: Database, between: Written) -> tuple[list[AuditEntry], int]:
    """Read a page of the whole journal, a second session writing ``between`` after its first read.

    The write comes once the first statement of the journal has run, by the cursor that ran it: a
    page read by two statements — the total, then the lines — has its second one see it.
    """
    pending = [between]

    def write_after_first_read(*arguments: Any) -> None:
        # The arguments of the event: the connection, the cursor, the statement, its parameters,
        # its context and whether it runs many.
        statement = str(arguments[2])
        if pending and statement.lstrip().startswith("SELECT") and "audit_entry" in statement:
            write(database, (pending.pop(),))

    event.listen(database.engine, "after_cursor_execute", write_after_first_read)
    try:
        with database.transaction() as session:
            page = list_entries(session, AuditFilters(), AuditSort(), limit=50, offset=0)
    finally:
        event.remove(database.engine, "after_cursor_execute", write_after_first_read)
    assert not pending
    return page.entries, page.total


def test_the_total_of_a_page_and_its_lines_are_read_on_one_snapshot(database: Database) -> None:
    # #928: an inscription a second session commits once the journal has been read once is in
    # neither the total nor the lines; read in two statements, the lines would hold it, and the
    # total not.
    write(database)
    entries, total = read_between(database, LATE)
    assert total == len(JOURNAL)
    assert len(entries) == total
    assert "req-late" not in {entry.correlation_id for entry in entries}
    with database.transaction() as session:
        again = list_entries(session, AuditFilters(), AuditSort(), limit=50, offset=0)
    assert (again.total, len(again.entries)) == (len(JOURNAL) + 1, len(JOURNAL) + 1)


def test_a_page_past_the_end_of_the_journal_is_empty_and_gives_the_total_all_the_same(
    database: Database,
) -> None:
    # The total comes with the page, by the same statement, even when the page holds no line.
    write(database)
    with database.transaction() as session:
        past = list_entries(session, AuditFilters(), AuditSort(), limit=5, offset=40)
        none = list_entries(session, AuditFilters(correlation_id="nowhere"), AuditSort(), 5, 0)
    assert (past.entries, past.total) == ([], len(JOURNAL))
    assert (none.entries, none.total) == ([], 0)


def test_the_page_keeps_its_order_and_its_window_whatever_the_total(database: Database) -> None:
    write(database)
    with database.transaction() as session:
        whole = list_entries(session, AuditFilters(), AuditSort(), limit=50, offset=0)
        second = list_entries(session, AuditFilters(), AuditSort(), limit=3, offset=3)
    assert [entry.id for entry in second.entries] == [entry.id for entry in whole.entries[3:6]]
    assert second.total == len(JOURNAL)


def grown(owner: Engine) -> int:
    """Copy the journal a hundred times beside the service; give how many inscriptions it holds."""
    with owner.begin() as connection:
        connection.execute(GROW, {"copies": COPIES})
        connection.execute(text("ANALYZE audit_entry"))
        return connection.scalar(text("SELECT count(*) FROM audit_entry")) or 0


def nodes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Give every node of a plan, the plan's own first."""
    found = [plan]
    for child in plan.get("Plans", []):
        found += nodes(child)
    return found


def reads_the_journal(node: dict[str, Any]) -> bool:
    """Tell whether a node scans the journal: by a sequence, an index or the heap."""
    return node.get("Relation Name") == "audit_entry" and "Scan" in node["Node Type"]


def explained(owner: Engine, key: Any) -> dict[str, Any]:
    """Give the plan, run, of the read of the latest inscription of each value of ``key``."""
    query = latest_first(key).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    with owner.begin() as connection:
        run = connection.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")).scalar_one()
    return run[0]["Plan"]


@pytest.mark.parametrize("key", list(COMPOSITE), ids=["authors", "projects"])
def test_a_facet_of_the_journal_of_the_set_reads_by_its_index_and_does_not_read_the_journal_whole(
    witness: Database, service_database_url: str, owner: Engine, key: Any
) -> None:
    # #934, on the set of reference (US-2950) loaded, its journal grown to its volumes: the latest
    # inscription of each author, and of each project, is one probe of the composite index, in its
    # own order — no scan of the journal in sequence, no sort of it, and as few lines read as
    # there are values, where a ``DISTINCT ON`` reads and sorts every one.
    del witness
    assert reference_load.load_reference(settings(service_database_url), PROJECTS, UNEXTENDED) == 0
    held = grown(owner)
    assert held > 50_000
    plan = explained(owner, key)
    journal = [node for node in nodes(plan) if reads_the_journal(node)]
    assert not [node for node in journal if node["Node Type"] == "Seq Scan"]
    probes = [node for node in journal if node.get("Index Name") == COMPOSITE[key]]
    assert probes, [node.get("Index Name") for node in journal]
    for node in nodes(plan):
        if node["Node Type"] in ("Sort", "Incremental Sort"):
            assert not [below for below in nodes(node) if reads_the_journal(below)], node
    values = plan["Actual Rows"]
    read = sum(node["Actual Rows"] * node["Actual Loops"] for node in journal)
    assert values >= 1
    assert read <= 3 * (values + 1) < held / 100


def test_the_facets_read_the_same_authors_and_projects_as_the_journal_names(
    database: Database,
) -> None:
    # The walk by the index gives what a ``DISTINCT ON`` gave: each author and each project once,
    # by the name of its latest inscription.
    write(database)
    with database.transaction() as session:
        actors = {actor.user_id: actor.display_name for actor in journal_actors(session)}
        projects = {project.project_id for project in journal_projects(session)}
    named = {each.actor.user_id: each.actor.display_name for each in JOURNAL if each.actor}
    assert actors == named
    assert projects == {each.project.project_id for each in JOURNAL if each.project}
