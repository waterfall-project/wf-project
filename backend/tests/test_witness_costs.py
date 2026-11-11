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
- the provisions and the coverage of the risks are EP-08's: no provision line, no nature provision
  among the remaining, a coverage at nought, the row numbers the line of provision shifts, the lines
  the occurrence of a risk merged counted as any line, and what depends on them — the total, the
  remaining of a subproject, the difference with the review before;
- the reference is the offer 100 until the merge of the amendment 1 (EP-08): the budgets of the
  subprojects, their margins and the margin on the reference are measured to it, the project names
  it, a task's budgeted amount is that of its lineage in the 100;
- the tasks a risk originates are EP-08's;
- the authors of the objects the platform writes, their counters, and the commands of a reader,
  which follow its rights.
"""

import json
import re
import shutil
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
from test_witness_lines import PROVISION, line_rows
from test_witness_lines_reads import READ_AT, by_role, deviations, keyed
from test_witness_projects import (
    PRJ_001,
    REVISION_100,
    REVISION_101,
    REVISION_102,
    UNREACHED,
    counts,
    example,
    instant,
    read,
    without,
)
from test_witness_tasks import difference, structure_of

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
# The extraction of April replayed, analysed at the event 18, expired the day after.
EXPIRED = UUID("01926f3a-7c00-7000-8000-000000000a12")
ANALYSED = 18
# The reception of the customer, excluded at the event 13 for its reason.
RECEPTION = UUID("01926f3a-7c00-7000-8000-000000000c04")
EXCLUDED = 13
REASON = "Réception du client, non budgétée"
# The imports of the chronology that write nothing yet: the planning abandoned (event 17, EP-06)
# and the estimate analysed (event 20, EP-07 and EP-08).
UNLOADED_IMPORTS = {
    "01926f3a-7c00-7000-8000-000000000a10": "ms_project_schedule",
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
        journal = {row.id: row for row in session.scalars(select(CostImport))}
        reports = {row.id: row for row in session.scalars(select(ImportReport))}
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
    assert len(reports) == 6


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_extraction_of_april_replayed_is_analysed_at_its_event_and_expired_the_day_after(
    witness: Database,
) -> None:
    analysed = example("import_actual_costs_analysed")
    with witness.transaction() as session:
        row = session.get(ImportReport, EXPIRED)
        applied = session.scalar(
            select(func.count())
            .select_from(CostImport)
            .where(CostImport.import_report_id == EXPIRED)
        )
    assert row is not None
    assert applied == 0
    assert (row.status, row.applied_at, row.task_id) == ("expired", None, None)
    assert row.analysed_at == instant(ANALYSED)
    assert row.expires_at == instant(ANALYSED) + LIFETIME
    assert row.report == analysed["report"]
    assert (row.filename, row.period_from, row.period_to) == (
        analysed["filename"],
        day(analysed["period_from"]),
        day(analysed["period_to"]),
    )


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
        rows = {row.id: row for row in session.scalars(select(CostLine))}
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
def test_the_imports_read_are_the_six_of_the_actual_costs_of_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The imports of the planning and of the estimate are not loaded (EP-06, EP-07, EP-08): the
    # others are the example's, in its order, the extraction of April replayed read expired.
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
    assert len(body["items"]) == 6
    assert body["meta"]["total"] == expected["meta"]["total"] - len(UNLOADED_IMPORTS)


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


# What the remaining indicators of the witness differ in from the example, each for its cause.
REMAINING_APART = {
    # The provision of the risk of the core (EP-08).
    "/total",
    "/by_cost_type[len]",
    "/by_cost_type[]/amount",
    "/by_cost_type[]/share/value",
    "/by_subproject[]/remaining",
    # Measured to the offer 100, the reference until the amendment 1 (EP-08).
    "/by_subproject[]/budget",
    "/by_subproject[]/variance",
    "/by_subproject[]/is_over_budget",
    "/by_subproject[]/zone",
    "/delta_to_reference",
    # The provisions of the revision in progress and of the review before (EP-08).
    "/delta_to_previous_revision",
    # The coverage of the risks, at nought without a risk (EP-08).
    "/coverage/reserve",
    "/coverage/remaining_provisions",
    "/coverage/occurred_cost",
    "/coverage/occurred_reestimated",
    "/coverage/coverage_variance",
}


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_remaining_indicators_are_the_example_but_for_the_provisions_and_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/remaining-indicators")
    expected = example("remaining_indicators")
    assert deviations(body, expected) == REMAINING_APART
    # The actual cost of each subproject is the example's: the costs the slice loaded.
    assert [each["actual_cost"] for each in body["by_subproject"]] == [
        each["actual_cost"] for each in expected["by_subproject"]
    ]
    # The natures of the example but the provision (EP-08); the total its, but for the provision
    # and the lines the occurrence of a risk merged (EP-08).
    provision = next(each for each in expected["by_cost_type"] if each["label"] == "Provision")
    assert [each["key"] for each in body["by_cost_type"]] == [
        each["key"] for each in expected["by_cost_type"] if each is not provision
    ]
    total = Decimal(body["total"])
    assert total == Decimal(expected["total"]) - Decimal(provision["amount"]) - merged()
    for dimension, amount in (("by_cost_type", "amount"), ("by_subproject", "remaining")):
        assert sum(Decimal(each[amount]) for each in body[dimension]) == total
    # Measured to the offer 100, each margin the budget less the actual cost and the remaining.
    with witness.transaction() as session:
        offer = sum(
            (facet.reestimated_amount for _, facet in line_rows(session, REVISION_100).values()),
            Decimal(0),
        )
    budgets = [Decimal(each["budget"]) for each in body["by_subproject"]]
    assert sum(budgets) == offer
    for each in body["by_subproject"]:
        margin = Decimal(each["budget"]) - Decimal(each["actual_cost"]) - Decimal(each["remaining"])
        assert Decimal(each["variance"]) == margin
        assert (each["is_over_budget"], each["zone"]) == (
            (True, "alert") if margin < 0 else (False, "nominal")
        )
    assert Decimal(body["delta_to_reference"]) == sum(
        Decimal(each["variance"]) for each in body["by_subproject"]
    )
    assert set(body["coverage"].values()) == {"0.00"}


def merged() -> Decimal:
    """Give the remaining the example counts of the lines the occurrence of a risk merged (EP-08).

    Budgeted at nought, at their re-estimated amount though their tasks are completed (WF-RAE-0010):
    the witness bears them without their risk, lines of completed tasks, out of the remaining.
    """
    items = keyed(example("volume/nodes_thousand")["items"], "node_id")
    found = [
        each["estimate_line"]["reestimated_amount"]
        for each in items.values()
        if each["kind"] == "estimate_line" and each["origin_risk_id"] is not None
    ]
    assert len(found) == 2
    return sum((Decimal(each) for each in found), Decimal(0))


# What the Kanban counts of the tasks whose amounts differ from the example's, by column and cause:
# the base amount of the core, which bears the provision (EP-08); the budgeted amount of a lineage
# in the offer 100, the reference; the re-estimated amount of a task bearing the provision.
AMOUNTS_APART = {
    "not_started": {"base_amount": 0, "budgeted_amount": 1, "reestimated_amount": 0},
    "started": {"base_amount": 1, "budgeted_amount": 1, "reestimated_amount": 1},
    "completed": {"base_amount": 0, "budgeted_amount": 0, "reestimated_amount": 0},
}
COLUMNS = ("not_started", "started", "completed")
COMMANDS = {"available_commands"}


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_kanban_is_the_example_but_for_the_provision_the_reference_and_the_commands(
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
    # The row numbers below the line of provision the witness lacks are one less (EP-08).
    gone = example("volume/nodes_thousand")["items"]
    absent = next(each["row_number"] for each in gone if each["node_id"] == PROVISION)
    for column in COLUMNS:
        got, wanted = keyed(body[column], "node_id"), keyed(expected[column], "node_id")
        # The same tasks in each column, in the order of the plan.
        assert list(got) == list(wanted), column
        found = dict.fromkeys(AMOUNTS_APART[column], 0)
        for key, card in got.items():
            theirs = wanted[key]
            assert not difference(without(card, COMMANDS), without(theirs, COMMANDS), read_on), (
                column,
                card["task"]["label"],
            )
            assert card["row_number"] == theirs["row_number"] - (theirs["row_number"] > absent)
            assert [each["predecessor_row_number"] for each in sorted_links(card)] == [
                each["predecessor_row_number"] - (each["predecessor_row_number"] > absent)
                for each in sorted_links(theirs)
            ]
            # The tasks a risk originates are EP-08's; the commands follow the reader's rights.
            assert card["origin_risk_id"] is None
            assert card["available_commands"] == []
            for amount in found:
                found[amount] += card["task"][amount] != theirs["task"][amount]
        assert found == AMOUNTS_APART[column], column
    assert [len(body[column]) for column in COLUMNS] == [925, 8, 27]


def sorted_links(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Give the predecessors of a card in the order of their nodes."""
    return sorted(card.get("predecessors") or [], key=lambda each: each["predecessor_node_id"])


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_workload_of_the_marked_remaining_is_the_example_within_a_rounding_of_a_hundredth(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The plan of the revision 101 at its marking, every role and every month; the service orders
    # the roles by the category of their nature, the example by their identifier.
    del the_day
    url = f"{PROJECTS}/{PRJ_001}/workload?basis=marked_remaining&revision_id={REVISION_101}"
    body = read(api, witness, realm, url)
    expected = example("workload_marked_remaining")
    assert deviations(by_role(body), by_role(expected), Decimal("0.02")) == set()
    assert body["context"] == {**expected["context"], "computed_at": body["context"]["computed_at"]}
    assert zulu(body["context"]["computed_at"]) == expected["context"]["computed_at"]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_project_read_is_the_example_but_for_the_reference_the_authors_and_the_counter(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["project"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}")
    assert without(body, unreached) == without(example("project"), unreached)
    assert body["reference_revision_id"] == str(REVISION_100)


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give the identifiers, imputations, instants and totals of the costs of the witness."""
    with database.transaction() as session:
        return {
            "cost_import": sorted(
                (row.id, row.import_report_id, row.imported_at, row.requested_by)
                for row in session.scalars(select(CostImport))
            ),
            "import": sorted(
                (row.id, row.status, row.created_at, row.analysed_at, row.applied_at)
                for row in session.scalars(select(ImportReport))
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
                for row in session.scalars(select(CostLine))
            ),
            "totals": [
                tuple(
                    session.execute(
                        select(CostLine.is_in_tracked_scope, func.sum(CostLine.amount))
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
    assert [len(first[name]) for name in ("cost_import", "import", "cost_line")] == [5, 6, 28]


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
    directory = tmp_path / "witness"
    shutil.copytree(WITNESS, directory)
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
        held.listing(EXPIRED, "applied")
    with pytest.raises(ValueError, match="lists no import"):
        held.listing(unknown, "expired")


def loaded_import(**changed: Any) -> ImportLoad:
    """Give the extraction of April replayed as the witness loads it, changed as said."""
    analysed = instant(ANALYSED)
    values: dict[str, Any] = {
        "import_id": EXPIRED,
        "project_id": PRJ_001,
        "kind": "actual_costs",
        "filename": "couts-reels-2026-04-correction.xlsx",
        "status": "expired",
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
        (loaded_import(), instant(ANALYSED) + LIFETIME, MANAGER, "instants"),
        (loaded_import(status="applied"), instant(ANALYSED) + 2 * LIFETIME, MANAGER, "instants"),
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
    # analysis, a day before its expiry, and that expiry; expired, it is the instant of its
    # analysis; opened before it is analysed; by an account.
    with pytest.raises(ValueError, match=cause):
        load_import(cast("Session", None), load, Act(author, at))
