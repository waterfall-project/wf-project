# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the actual costs of the witness, and its readings (US-1650/L2; WF-QUA-0040-A).

Laid by US-1580/L1, the socle of EP-09; US-1650/L2 writes its tests here ("Les tests du back").
``load-witness`` writes, at the events of the chronology, the five imports of actual costs of
PRJ-001 — the import of the exchanges in its state with its report, the entry of the journal, the
lines created or updated —, the exclusion of the reception of the customer on 6 April at 9:15, and
the extraction of April replayed, analysed on 2 June and expired the day after, each at the
identifiers of ``witness_costs.json`` and the instants of the chronology, by the project manager of
the witness.

What the service reads of the loaded witness is compared with the examples of the contract. The
readings of the costs are the examples, audit columns included; the others differ only where the
witness does not reach, each named with its cause where the test stands:

- the imports of the planning (``a10``, EP-06) and of the estimate (``a11``, EP-07, EP-08), events
  of the chronology without a write, are not loaded: the list holds the six of the actual costs;
- the authors of the objects the platform writes, their counters, and the commands of a reader,
  which follow its rights; the identifiers of the tasks of a marked revision, the witness's own.

Since EP-08 (US-2650/L1), the reference is the 101 the merge of the amendment 1 marks, and the risks
bear their provision lines and their coverage: what the examples read of them is read without
reserve.
"""

import json
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from installed_reference import install
from projects_support import PROJECTS
from sqlalchemy import func, select
from support import WITNESS, captured_logs
from test_witness import load, wipe
from test_witness_lines_reads import (
    by_role,
    deviations,
    keyed,
    tasks_are_their_nodes,
)
from test_witness_projects import (
    REVISION_101,
    REVISION_102,
    UNREACHED,
    counts,
    instant,
    without,
)
from test_witness_tasks import difference, structure_of
from witness_support import PRJ_001, READ_AT, copied_description, example, read

from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.exchanges.interface import ImportLoad, load_import
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act, AuditEntry
from waterfall.witness import costs as costs_slice
from waterfall.witness.description import Witness

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

# The project manager of the witness, Camille Martin, who applies the imports and excludes the line.
MANAGER = UUID("01926f3a-7c00-7000-8000-000000000301")
# The extraction of April replayed, analysed at the event 23, expired the day after: the purge
# deletes it in the pass that finds it so, and the witness loads nothing of it (US-3250).
EXPIRED = UUID("01926f3a-7c00-7000-8000-000000000a12")
ANALYSED = 23
# The reception of the customer, excluded at the event 18 for its reason.
RECEPTION = UUID("01926f3a-7c00-7000-8000-000000000c04")
EXCLUDED = 18
REASON = "Réception du client, non budgétée"
# The import of the chronology that writes nothing yet: the estimate analysed (event 25, EP-07 and
# EP-08). The planning abandoned and the extraction expired are no longer listed (US-3250).
UNLOADED_IMPORTS = {
    "01926f3a-7c00-7000-8000-000000000a11": "estimate",
}
COMMAND_POST = "01926f3a-7c00-7000-8000-000000000801"
LIFETIME = timedelta(hours=24)
COUNTS = ("created_count", "updated_count", "unchanged_count", "rejected_count")

# The readings of the costs, which are the examples, audit columns included.
COSTS_READS = {
    "actual_costs": "/actual-costs",
    "actual_costs_page": "/actual-costs?limit=1&offset=1",
    "actual_costs_subproject": f"/actual-costs?subproject_id={COMMAND_POST}",
    "cost_imports": "/cost-imports",
}


def described() -> dict[str, Any]:
    """Read the description of the costs the witness is loaded with."""
    return example("witness_costs")


def day(text: str | None) -> date | None:
    """Read a day of the description, ``None`` for a missing one."""
    return None if text is None else date.fromisoformat(text)


def zulu(text: str) -> str:
    """Write an instant as the examples do."""
    return text.replace("+00:00", "Z")


@pytest.fixture
def the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the instant the service reads as now to that of the examples, 3 June 2026 at 14:05."""
    for module in ("workload", "remaining_indicators", "imports"):
        monkeypatch.setattr(f"waterfall.api.{module}.utc_now", lambda: READ_AT)


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_five_imports_of_costs_are_loaded_at_their_events_by_the_manager(
    witness: Database,
) -> None:
    # The journal and the imports of the exchanges that applied them: identifiers, instants,
    # periods, columns kept, counts and reports those of the description, the application at the
    # instant of its event, by the manager, analysed a day before the report expires, without a
    # deposit the storage holds and without a task.
    entries = {UUID(each["cost_import_id"]): each for each in described()["imports"]}
    listed = keyed(example("imports")["items"], "import_id")
    with witness.transaction() as session:
        journal = {
            row.id: row
            for row in session.scalars(select(CostImport).where(CostImport.project_id == PRJ_001))
        }
        reports = {
            row.id: row
            for row in session.scalars(
                select(ImportReport).where(ImportReport.project_id == PRJ_001)
            )
        }
    assert journal.keys() == entries.keys()
    assert len(journal) == 5
    for cost_import_id, row in journal.items():
        entry = entries[cost_import_id]
        assert row.project_id == PRJ_001
        assert zulu(row.imported_at.isoformat()) == entry["imported_at"]
        assert (row.requested_by, str(row.import_report_id)) == (MANAGER, entry["import_id"])
        assert (row.period_from, row.period_to) == (
            day(entry["period_from"]),
            day(entry["period_to"]),
        )
        assert row.passthrough_columns == entry["kept_columns"]
        assert [getattr(row, count) for count in COUNTS] == [entry[count] for count in COUNTS]
        report = reports[row.import_report_id]
        item = listed[str(report.id)]
        assert (report.kind, report.status, report.filename) == (
            "actual_costs",
            "applied",
            item["filename"],
        )
        assert (report.task_id, report.requested_by, report.report) == (
            None,
            MANAGER,
            entry["report"],
        )
        assert report.expires_at is not None
        assert report.analysed_at == report.expires_at - LIFETIME
        assert report.applied_at == row.imported_at
        assert zulu(report.created_at.isoformat()) == item["created_at"]
    assert len(reports) == 5


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_witness_keeps_no_import_the_purge_deletes_neither_expired_nor_abandoned(
    witness: Database,
) -> None:
    # The extraction of April replayed is not loaded, nor is any import expired or abandoned: the
    # purge deletes them in the pass that finds them so, and the witness keeps nothing beyond it.
    with witness.transaction() as session:
        row = session.get(ImportReport, EXPIRED)
        statuses = set(session.scalars(select(ImportReport.status)))
    assert row is None
    assert statuses.isdisjoint({"expired", "abandoned"})


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_twenty_eight_lines_are_those_of_the_description_imputed_by_the_service(
    witness: Database,
) -> None:
    # Each line at its identifier, with its document, its item, its date, its amount, its code and
    # its columns kept; imputed by the service to the subproject its code names — the one the
    # description computed —; created at the instant of the import that brought it, updated at that
    # of the last that brought it again, which it names; by the manager.
    instants = {each["cost_import_id"]: each["imported_at"] for each in described()["imports"]}
    lines = {UUID(each["cost_line_id"]): each for each in described()["lines"]}
    with witness.transaction() as session:
        rows = {
            row.id: row
            for row in session.scalars(select(CostLine).where(CostLine.project_id == PRJ_001))
        }
    assert rows.keys() == lines.keys()
    assert len(rows) == 28
    for line_id, row in rows.items():
        line = lines[line_id]
        last = [line["created_by_cost_import_id"], *line["updated_by_cost_import_ids"]][-1]
        assert row.project_id == PRJ_001
        assert (row.document_number, row.document_item) == (
            line["document_number"],
            line["document_item"],
        )
        assert (row.document_date, row.amount) == (
            day(line["document_date"]),
            Decimal(line["amount"]),
        )
        assert (row.subproject_code, row.passthrough) == (
            line["subproject_code"],
            line["passthrough"],
        )
        assert row.subproject_id == (
            None if line["subproject_id"] is None else UUID(line["subproject_id"])
        )
        assert str(row.last_import_id) == last
        assert zulu(row.created_at.isoformat()) == instants[line["created_by_cost_import_id"]]
        assert zulu(row.updated_at.isoformat()) == instants[last]
        assert (row.created_by, row.updated_by) == (MANAGER, MANAGER)
        assert row.is_in_tracked_scope == (line["excluded"] is None)
    assert [row.id for row in rows.values() if not row.is_in_tracked_scope] == [RECEPTION]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_reception_of_the_customer_is_excluded_at_its_event_for_its_reason(
    witness: Database,
) -> None:
    # Excluded on 6 April at 9:15, three days after its import, by the manager, inscribed in the
    # journal of audit as the service excludes; the imports after it keep the exclusion.
    with witness.transaction() as session:
        line = session.get(CostLine, RECEPTION)
        inscribed = session.execute(
            select(AuditEntry.action, AuditEntry.occurred_at, AuditEntry.actor_user_id).where(
                AuditEntry.object_id == RECEPTION
            )
        ).all()
    assert line is not None
    assert (line.is_in_tracked_scope, line.excluded_reason) == (False, REASON)
    assert [tuple(each) for each in inscribed] == [
        ("cost_line_exclude", instant(EXCLUDED), MANAGER)
    ]
    assert line.updated_at > instant(EXCLUDED)


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize("name", list(COSTS_READS))
def test_the_readings_of_the_costs_are_the_examples_audit_columns_included(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}{COSTS_READS[name]}")
    assert deviations(body, example(name)) == set()


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_imports_read_are_the_five_of_the_actual_costs_of_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The import of the estimate is not loaded (EP-07, EP-08): the others are the example's, in its
    # order.
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/imports")
    expected = example("imports")
    wanted = [each for each in expected["items"] if each["import_id"] not in UNLOADED_IMPORTS]
    assert {
        each["import_id"]: each["kind"]
        for each in expected["items"]
        if each["import_id"] in UNLOADED_IMPORTS
    } == UNLOADED_IMPORTS
    assert deviations(body["items"], wanted) == set()
    assert len(body["items"]) == 5
    assert body["meta"]["total"] == expected["meta"]["total"] - len(UNLOADED_IMPORTS)


@pytest.mark.requirement("WF-DAT-0080-A")
def test_each_import_of_the_witness_is_read_without_a_task_not_a_500(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The imports of the witness never had a task: ``getImport`` answers 200, its task null, for
    # each (US-3250); the example of the list is the answer of the service on them.
    del the_day
    listed = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/imports")["items"]
    assert len(listed) == 5
    for item in listed:
        found = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/imports/{item['import_id']}")
        assert found["task"] is None
        assert found["status"] == "applied"
        assert found["report"] is not None


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_subprojects_with_actual_costs_are_the_example_but_for_the_authors_and_counters(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The two subprojects bear actual costs, and can no longer be deleted.
    unreached = set(UNREACHED["subproject"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/subprojects?has_actual_costs=true")
    expected = example("subprojects_with_actual_costs")
    assert without(body, unreached) == without(expected, unreached)
    assert [each["has_actual_costs"] for each in body] == [True, True]


# What the remaining of the day differs in from the example: the lines the occurrence of 752
# grafted, of tasks completed, which the example counts at their re-estimate (#4278).
REMAINING_APART = {
    "/total",
    "/by_cost_type[]/amount",
    "/by_subproject[]/remaining",
    "/by_subproject[]/variance",
    "/delta_to_reference",
    "/delta_to_previous_revision",
}


def occurred() -> Decimal:
    """Give the re-estimate of the lines the occurrence of 752 grafted, which the examples count."""
    items = keyed(example("volume/nodes_thousand")["items"], "node_id")
    found = [
        Decimal(each["estimate_line"]["reestimated_amount"])
        for each in items.values()
        if each["kind"] == "estimate_line" and each["origin_risk_id"] is not None
    ]
    assert len(found) == 2
    return sum(found, Decimal(0))


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_remaining_indicators_are_the_example_but_for_the_lines_of_the_occurrence(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The provisions and the coverage of the risks, the budgets of the subprojects and the margins
    # measured to the 101, the reference (EP-08), are the example's; the total, out of any
    # subproject, falls short by the lines of the occurrence (#4278), the margins as much.
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/remaining-indicators")
    expected = example("remaining_indicators")
    assert deviations(body, expected) == REMAINING_APART
    assert Decimal(expected["total"]) - Decimal(body["total"]) == occurred()
    gaps = {
        each["key"]: Decimal(theirs["remaining"]) - Decimal(each["remaining"])
        for each, theirs in zip(body["by_subproject"], expected["by_subproject"], strict=True)
    }
    assert {key: gap for key, gap in gaps.items() if gap} == {"unassigned": occurred()}
    for dimension, amount in (("by_cost_type", "amount"), ("by_subproject", "remaining")):
        assert sum(Decimal(each[amount]) for each in body[dimension]) == Decimal(body["total"])
    for each in body["by_subproject"]:
        margin = Decimal(each["budget"]) - Decimal(each["actual_cost"]) - Decimal(each["remaining"])
        assert Decimal(each["variance"]) == margin
    assert body["coverage"] == expected["coverage"]


COLUMNS = ("not_started", "started", "completed")
COMMANDS = {"available_commands"}


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_kanban_is_the_example_but_for_the_commands(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/remaining-indicators/startable-tasks")
    expected = example("startable_tasks")
    # A task started is overdue against the day the current revision was scheduled (EP-07).
    with witness.transaction() as session:
        scheduled = session.get(CostStructure, (PRJ_001, structure_of(session, REVISION_102)))
        assert scheduled is not None
        assert scheduled.scheduled_at is not None
        read_on = scheduled.scheduled_at.date()
    for column in COLUMNS:
        got, wanted = keyed(body[column], "node_id"), keyed(expected[column], "node_id")
        # The same tasks in each column, in the order of the plan.
        assert list(got) == list(wanted), column
        for key, card in got.items():
            theirs = wanted[key]
            assert not difference(without(card, COMMANDS), without(theirs, COMMANDS), read_on), (
                column,
                card["task"]["label"],
            )
            assert card["row_number"] == theirs["row_number"]
            assert sorted_links(card) == sorted_links(theirs)
            # The risk a task comes from (EP-08); the commands follow the reader's rights.
            assert card["origin_risk_id"] == theirs["origin_risk_id"]
            assert card["available_commands"] == []
            # The budgeted amount with the provision the reference fixed, that a task bears (#4274).
            for amount in ("base_amount", "budgeted_amount", "reestimated_amount"):
                assert card["task"][amount] == theirs["task"][amount], (key, amount)
    assert [len(body[column]) for column in COLUMNS] == [925, 8, 27]


def sorted_links(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Give the predecessors of a card in the order of their nodes."""
    return sorted(card.get("predecessors") or [], key=lambda each: each["predecessor_node_id"])


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_workload_of_the_marked_remaining_is_the_example_within_a_rounding_of_a_hundredth(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The plan of the revision 101 at its marking, every role and every month; the service orders
    # the roles by the category of their nature, the example by their identifier.
    del the_day
    url = f"{PROJECTS}/{PRJ_001}/workload?basis=marked_remaining&revision_id={REVISION_101}"
    body = read(api, witness, realm, url)
    expected = example("workload_marked_remaining")
    # The detail of each role too (WF-DEV-0090), its rows the example's, but for the identifiers
    # of the tasks, the witness's own in a marked revision.
    aside = {"node_id"}
    ours, theirs = by_role(without(body, aside)), by_role(without(expected, aside))
    assert deviations(ours, theirs, Decimal("0.02")) == set()
    tasks_are_their_nodes(api, witness, realm, body, REVISION_101)
    assert body["context"] == {**expected["context"], "computed_at": body["context"]["computed_at"]}
    assert zulu(body["context"]["computed_at"]) == expected["context"]["computed_at"]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_project_read_is_the_example_but_for_the_authors_and_the_counter(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["project"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}")
    assert without(body, unreached) == without(example("project"), unreached)
    assert body["reference_revision_id"] == str(REVISION_101)


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give the identifiers, imputations, instants and totals of the costs of the witness."""
    with database.transaction() as session:
        return {
            "cost_import": sorted(
                (row.id, row.import_report_id, row.imported_at, row.requested_by)
                for row in session.scalars(
                    select(CostImport).where(CostImport.project_id == PRJ_001)
                )
            ),
            "import": sorted(
                (row.id, row.status, row.created_at, row.analysed_at, row.applied_at)
                for row in session.scalars(
                    select(ImportReport).where(ImportReport.project_id == PRJ_001)
                )
            ),
            "cost_line": sorted(
                (
                    row.id,
                    row.subproject_id,
                    row.amount,
                    row.is_in_tracked_scope,
                    row.last_import_id,
                    row.updated_at,
                )
                for row in session.scalars(select(CostLine).where(CostLine.project_id == PRJ_001))
            ),
            "totals": [
                tuple(
                    session.execute(
                        select(CostLine.is_in_tracked_scope, func.sum(CostLine.amount))
                        .where(CostLine.project_id == PRJ_001)
                        .group_by(CostLine.is_in_tracked_scope)
                        .order_by(CostLine.is_in_tracked_scope)
                    ).all()
                )
            ],
        }


@pytest.mark.requirement("WF-QUA-0040-A")
def test_two_new_platforms_loaded_with_the_witness_hold_the_same_costs(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    first = identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying(witness) == first
    assert [len(first[name]) for name in ("cost_import", "import", "cost_line")] == [5, 5, 28]


# An address of electronic mail, wherever it stands in a text.
MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def texts(value: object) -> list[str]:
    """Give every text of a value of the description, keys included."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        mapped = cast("dict[str, object]", value)
        return [text for key, each in mapped.items() for text in (key, *texts(each))]
    if isinstance(value, list):
        listed = cast("list[object]", value)
        return [text for each in listed for text in texts(each)]
    return []


@pytest.mark.requirement("WF-QUA-0040-A")
def test_no_address_and_no_project_but_the_witness_s_appear_in_the_costs() -> None:
    # The suppliers and the documents are the witness's, fictitious: no address of mail anywhere,
    # and the only projects the file names, by their code in the elements of the work breakdown
    # structure its lines rejected, are the witness's.
    found = texts(described())
    assert not [text for text in found if MAIL.search(text)]
    codes = {code for text in found for code in re.findall(r"\bPRJ-\d+", text)}
    projects = {each["code"] for each in example("projects")["items"]}
    assert codes
    assert codes <= projects == {"PRJ-001", "PRJ-002"}


def copied(tmp_path: Path, name: str, mutate: Any) -> Path:
    """Copy the description of the witness, the file ``name`` changed by ``mutate``."""
    directory = copied_description(tmp_path)
    path = directory / name
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document["value"])
    path.write_text(json.dumps(document), encoding="utf-8")
    return directory


def stray_field(value: dict[str, Any]) -> None:
    """Add a field beyond the model to the first line of cost."""
    value["lines"][0]["beyond"] = True


def applied_elsewhere(value: dict[str, Any]) -> None:
    """Say the first import was applied an hour after its event."""
    value["imports"][0]["imported_at"] = "2026-04-03T09:30:00Z"


def excluded_otherwise(value: dict[str, Any]) -> None:
    """Give the reception of the customer another reason than its event's."""
    line = next(each for each in value["lines"] if each["cost_line_id"] == str(RECEPTION))
    line["excluded"]["reason"] = "Autre motif"


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize(
    "case",
    [
        (stray_field, "Extra inputs are not permitted"),
        (applied_elsewhere, "is not applied at its event"),
        (excluded_otherwise, "does not exclude the line FA-2026-0295 as the chronology does"),
    ],
)
def test_a_description_of_the_costs_that_strays_stops_the_command_nothing_written(
    case: tuple[Any, str],
    tmp_path: Path,
    witness: Database,
    owner: Engine,
    service_database_url: str,
) -> None:
    mutate, cause = case
    wipe(owner)
    install(owner)
    before = counts(witness)
    directory = copied(tmp_path, "witness_costs.json", mutate)
    with captured_logs() as logs:
        assert load(service_database_url, directory) == 1
    (failed,) = logs.named("witness.failed")
    assert cause in failed["exception"]
    assert counts(witness) == before
    with witness.transaction() as session:
        assert session.scalar(select(func.count()).select_from(CostLine)) == 0


def description() -> costs_slice.Costs:
    """Read what the slice of the costs reads of the description of the witness."""
    return costs_slice.Costs.read(Witness(WITNESS, Act(None, READ_AT)))


@pytest.mark.requirement("WF-QUA-0040-A")
def test_an_import_a_line_or_a_listing_the_description_lacks_is_refused_by_name() -> None:
    held = description()
    unknown = UUID("01926f3a-7c00-7000-8000-000000000c99")
    with pytest.raises(ValueError, match="names an import of costs"):
        held.entry(unknown)
    with pytest.raises(ValueError, match="names a line FA-2026-9999"):
        held.line("FA-2026-9999", "10")
    with pytest.raises(ValueError, match="lists no import"):
        held.listing(EXPIRED)
    with pytest.raises(ValueError, match="lists no import"):
        held.listing(unknown)


def loaded_import(**changed: Any) -> ImportLoad:
    """Give an extraction of April as the witness loads it, applied, changed as said."""
    analysed = instant(ANALYSED)
    values: dict[str, Any] = {
        "import_id": EXPIRED,
        "project_id": PRJ_001,
        "kind": "actual_costs",
        "filename": "couts-reels-2026-04-correction.xlsx",
        "period_from": None,
        "period_to": None,
        "report": {},
        "created_at": analysed - timedelta(minutes=1),
        "expires_at": analysed + LIFETIME,
    }
    return ImportLoad(**{**values, **changed})


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize(
    ("load", "at", "author", "cause"),
    [
        (loaded_import(), instant(ANALYSED), None, "has no author"),
        (loaded_import(), instant(ANALYSED) - timedelta(seconds=1), MANAGER, "instants"),
        (loaded_import(), instant(ANALYSED) + 2 * LIFETIME, MANAGER, "instants"),
        (
            loaded_import(created_at=instant(ANALYSED) + LIFETIME),
            instant(ANALYSED),
            MANAGER,
            "instants",
        ),
    ],
)
def test_an_import_of_the_witness_whose_author_or_instants_disagree_is_refused_unwritten(
    load: ImportLoad, at: datetime, author: UUID | None, cause: str
) -> None:
    # Refused before any write: no session is touched. Applied, its instant falls between its
    # analysis, a day before its expiry, and that expiry; opened before it is analysed; by an
    # account.
    with pytest.raises(ValueError, match=cause):
        load_import(cast("Session", None), load, Act(author, at))
