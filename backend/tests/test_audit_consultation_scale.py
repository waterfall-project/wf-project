# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The consultation of the journal at its scale: a page on one snapshot, the facets by indexes.

The total of a page and its lines are read on one snapshot, two sessions meeting between the two
readings (#928); the facets, which name each author and each project of the journal, do not read
the journal whole, tried on the set of reference loaded (US-2950) and a journal grown to its
volumes (#934). Both are the criteria of US-2980 that belong to it. The journal of a project of the
set that its life completed is read five years after its closing, the purge having run on it
(WF-SEC-0030).
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import pytest
from projects_support import person
from sqlalchemy import event, func, select, text
from sqlalchemy.dialects import postgresql
from task_handlers import deposit, task
from test_audit_consultation import CLAIRE, JOURNAL, Written, at, write
from test_witness_reference import UNEXTENDED, settings

from waterfall.core.projects.tables import Project
from waterfall.platform.audit import AuditEntry
from waterfall.platform.audit_consultation import (
    AuditFilters,
    AuditSort,
    journal_actors,
    journal_projects,
    latest_first,
    list_entries,
    page_statement,
)
from waterfall.witness import reference_load
from waterfall.worker import purge as purge_module
from waterfall.worker.purge import PurgeTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket

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

    The write comes once the statement that counts the journal has run, by the cursor that ran it:
    a page read by two statements — the total, then the lines — has its second one see it, whatever
    was read of the journal before.
    """
    pending = [between]

    def write_after_first_read(*arguments: Any) -> None:
        # The arguments of the event: the connection, the cursor, the statement, its parameters,
        # its context and whether it runs many.
        statement = str(arguments[2]).lower()
        if pending and "count(" in statement and "audit_entry" in statement:
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


def explained(owner: Engine, statement: Any) -> dict[str, Any]:
    """Give the plan, run, of a statement."""
    query = statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    with owner.begin() as connection:
        run = connection.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")).scalar_one()
    return run[0]["Plan"]


def assert_page_read_by_the_dates(owner: Engine, held: int, offset: int) -> None:
    """Check the page by default is read by the index of the dates and the journal not sorted whole.

    Under the page, the journal is read backward by the index of the dates, as far as the page
    reaches and no further: the window that ranks the page reads the lines it holds, it does not
    wait for the journal sorted. The only sort left is of the lines of the page, once joined to the
    total, which reads the journal whole, as it always did.
    """
    limit = 50
    plan = explained(owner, page_statement(AuditFilters(), AuditSort(), limit, offset))
    under = [node for node in nodes(plan) if node["Node Type"] == "Limit"]
    assert len(under) == 1
    journal = [node for node in nodes(under[0]) if reads_the_journal(node)]
    assert [node["Node Type"] for node in journal] == ["Index Scan"]
    assert journal[0]["Scan Direction"] == "Backward"
    assert journal[0]["Actual Rows"] <= offset + limit + held // 100
    for node in nodes(plan):
        if node["Node Type"] == "Sort":
            assert node["Actual Rows"] <= limit, node


def assert_facet_read_by_its_index(owner: Engine, held: int, key: Any) -> None:
    """Check the latest inscription of each value of ``key`` is one probe of its composite index."""
    plan = explained(owner, latest_first(key))
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


def test_the_journal_of_the_set_is_read_by_its_indexes_for_its_page_and_for_its_facets(
    witness: Database, service_database_url: str, owner: Engine
) -> None:
    # #934, on the set of reference (US-2950) loaded, its journal grown to its volumes: the latest
    # inscription of each author, and of each project, is one probe of the composite index, in its
    # own order — no scan of the journal in sequence, no sort of it, and as few lines read as
    # there are values, where a ``DISTINCT ON`` reads and sorts every one. #928 must not cost the
    # page what it had: the first page and a deep one are read by the index of the dates. One
    # loading serves all of them: the journal is grown once, which is what takes the time.
    del witness
    assert reference_load.load_reference(settings(service_database_url), PROJECTS, UNEXTENDED) == 0
    held = grown(owner)
    assert held > 50_000
    for key in COMPOSITE:
        assert_facet_read_by_its_index(owner, held, key)
    for offset in (0, 50_000):
        assert_page_read_by_the_dates(owner, held, offset)


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


def project_journal(api: ContractClient, headers: dict[str, str], project_id: UUID) -> Any:
    """Read the whole journal of a project, oldest first, as a reader of it does."""
    query = urlencode({"project_id": str(project_id), "sort_order": "asc", "limit": 500})
    response = api.get(f"/api/v1/audit-events?{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def purging(
    witness: Database, queue: TaskQueue, backups_bucket: Bucket, monkeypatch: pytest.MonkeyPatch
) -> Callable[[datetime], None]:
    """Give a purge the worker runs as of an instant: the clock the platform reads stands there."""

    def purge_at(now: datetime) -> None:
        monkeypatch.setattr(purge_module, "utc_now", lambda: now)
        queue.prepare()
        task_id = deposit(witness, queue, "purge")
        handlers = {"purge": PurgeTask(backups_bucket, timedelta(hours=12), timedelta(days=30))}
        assert Worker(witness, queue, handlers, "worker", Timing(block=0.1)).step()
        assert task(witness, task_id).status == "succeeded"

    return purge_at


@pytest.fixture
def loaded_set(witness: Database, service_database_url: str) -> Database:
    """Give the database the set of reference is loaded on, by the command (US-2950)."""
    assert reference_load.load_reference(settings(service_database_url), PROJECTS, UNEXTENDED) == 0
    return witness


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_journal_of_a_project_completed_five_years_ago_is_consultable_on_the_set(
    loaded_set: Database, api: ContractClient, realm: TestRealm, purging: Callable[[datetime], None]
) -> None:
    # « Le journal d'un projet terminé depuis cinq ans est toujours consultable. » : a project
    # of the set of reference (US-2950) that its life completed, its journal read as a reader of it
    # does; the clock then stands five years after its closing, and the purge — what the platform
    # removes with time — runs on the set. The journal, which no process of the platform expires
    # (« conservé aussi longtemps que les projets »), is read again: whole, as it was, each
    # inscription older than five years.
    with loaded_set.transaction() as session:
        completed = session.scalars(
            select(Project).where(Project.state == "completed").order_by(Project.code)
        ).first()
        assert completed is not None
        closing = session.scalars(
            select(AuditEntry.occurred_at).where(
                AuditEntry.project_id == completed.id, AuditEntry.action == "project_exit"
            )
        ).one()
        held = session.scalar(select(func.count()).select_from(AuditEntry)) or 0
        code, label = completed.code, completed.label
    reader = person(loaded_set, realm, "audit_log.read", "all_projects_read")
    before = project_journal(api, reader.headers, completed.id)
    actions = {event["action"] for event in before["items"]}
    assert {"project_create", "revision_mark", "project_exit"} <= actions
    assert before["meta"]["total"] == len(before["items"]) >= 3
    last = before["items"][-1]
    assert (last["action"], last["params"]["to_state"]) == ("project_exit", "completed")
    assert last["project"] == {
        "project_id": str(completed.id),
        "code": code,
        "label": label,
        "can_open": True,
    }
    five_years_later = closing.replace(year=closing.year + 5) + timedelta(days=1)
    purging(five_years_later)
    after = project_journal(api, reader.headers, completed.id)
    assert after == before
    assert all(
        five_years_later - datetime.fromisoformat(event["occurred_at"]) > timedelta(days=5 * 365)
        for event in after["items"]
    )
    with loaded_set.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuditEntry)) == held
