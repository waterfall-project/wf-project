# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the lines of the witness (US-1570/L2; WF-QUA-0040, WF-CYC-0030): loaded and read.

``load-witness`` fills each revision of PRJ-001 once the slice of the revisions has opened it, after
its tasks and before it is marked (``witness.estimate_lines``): the lines the copy gave it
reconciled by lineage with those ``witness_lines.json`` describes — deleted, changed, created —
through the interface of the estimate, at the identifiers and the instants the witness imposes. The
slice of the revisions then accepts the update of the rates on the 101 (event 6) and designates the
offer 100 the reference (event 7), the project passing In progress when its code is entered.

What the service reads of the loaded witness is compared with the examples of the contract
(``nodes_estimate*``, ``volume/nodes_thousand``, ``estimate_indicators``, ``workload*``,
``contributor_suggestions``, ``revisions``, ``project``, ``comparison*``), amounts and audit columns
included, but for what the witness does not reach, each listed here, with its cause:

- the reference is the offer 100 until the merge of the amendment 1 (EP-08): the budgeted amount of
  a line is that of its lineage in the 100, where the examples read the 101's (``BUDGETS``), the
  indicators and the comparisons are measured to it, the project and the revisions name it;
- the provisions are EP-08's, the risks' lines (``PROVISIONS``): a line of provision is absent, with
  the row numbers it shifts and the amounts it adds to the tasks above it, the totals, the
  indicators and the comparisons;
- the figures of the previous revision (``previous_*``), the actual costs that lock the subproject
  of a line (``editable_fields``) are EP-09's;
- a line whose task straddles two years is spread over them by the service, by the hours of each
  (WF-DEV-0040), where the generator of the examples kept the first year (``STRADDLING``);
- the accounts of the witness are not attached to their node of the organisation, so that no
  contributor is suggested (``contributor_suggestions``); the authors are the platform's, and the
  commands of a reader are those of its rights, not of the example's.
"""

from collections import Counter
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from installed_reference import install
from sqlalchemy import func, select
from test_witness import load, wipe
from test_witness_projects import (
    PRJ_001,
    REVISION_100,
    REVISION_101,
    REVISION_102,
    example,
    instant,
)
from test_witness_tasks import REVISIONS, structure_of

from waterfall.core.estimate.interface import LineEntry, LineLoad, load_lines
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.interface import Place
from waterfall.core.planning.tables import Node
from waterfall.core.projects.tables import Project, ProjectStateTransition
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

LINES = "witness_lines"
# The events: the revisions opened, the rates accepted on the 101, the order received.
OPENED = {100: 3, 101: 5, 102: 9}
RATES_UPDATED, ORDER_RECEIVED = 6, 7
RATED = {
    UUID("01926f3a-7c00-7000-8000-000000000402"),
    UUID("01926f3a-7c00-7000-8000-000000000405"),
}
INSTALLATION = UUID("01926f3a-7c00-7000-8000-000000000661")
# The day of the reading of the examples: the 3 June 2026, 14:05.
READ_AT = datetime(2026, 6, 3, 14, 5, tzinfo=UTC)
ENTERED = frozenset(
    {
        "label",
        "cost_category_id",
        "resource_role_id",
        "quantity",
        "hours",
        "unit_disbursement",
        "payment_delay_days",
        "subproject_id",
    }
)
CABLER = UUID("01926f3a-7c00-7000-8000-000000000454")
# What a line of the examples carries that the witness does not (EP-09): the previous figures.
PREVIOUS = {
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
}
# What the service computes otherwise than the examples, compared apart, line by line.
APART = PREVIOUS | {"budgeted_amount", "reestimated_amount", "consumption_year"}
# The line of provision the examples read under the core (EP-08).
PROVISION = "01926f3a-7c00-7000-8000-000000000555"
CENT = Decimal("0.01")


def described() -> dict[str, Any]:
    """Read the value of ``witness_lines.json``."""
    return example(LINES)


def file_lines(revision: int) -> list[dict[str, Any]]:
    """Give the lines the file describes for a revision, in the order of the plan."""
    return [line for line in described()["lines"] if line["revision"] == revision]


def line_rows(session: Session, revision: UUID) -> dict[UUID, tuple[Node, EstimateLine]]:
    """Give the node and the facet of each line of a revision, by lineage."""
    found = session.execute(
        select(Node, EstimateLine)
        .join(
            EstimateLine,
            (EstimateLine.project_id == Node.project_id) & (EstimateLine.node_id == Node.id),
        )
        .where(Node.revision_id == revision)
    ).all()
    return {node.lineage_id: (node, facet) for node, facet in found}


def task_lineages(session: Session, revision: UUID) -> dict[UUID, UUID]:
    """Give the lineage of each task of a revision, by node."""
    found = session.execute(
        select(Node.id, Node.lineage_id).where(Node.revision_id == revision, Node.kind == "task")
    ).all()
    return dict(found)


def facet_of(line: dict[str, Any]) -> dict[str, object]:
    """Give what a line of the file enters, as the facet of the service holds it."""
    return {
        "label": line["label"],
        "cost_category_id": UUID(line["cost_category_id"]),
        "resource_role_id": None
        if line["resource_role_id"] is None
        else UUID(line["resource_role_id"]),
        "quantity": Decimal(line["quantity"]),
        "hours": None if line["hours"] is None else Decimal(line["hours"]),
        "unit_disbursement": None
        if line["unit_disbursement"] is None
        else Decimal(line["unit_disbursement"]),
        "payment_delay_days": line["payment_delay_days"],
        "subproject_id": None if line["subproject_id"] is None else UUID(line["subproject_id"]),
    }


def test_each_revision_holds_the_lines_the_file_describes_under_their_lineages_and_tasks(
    witness: Database,
) -> None:
    # 4 997, 4 997 and 4 999 lines: the same lineages as the file, under the task it names, at the
    # rank of their position among the lines of that task, entered as the file enters them.
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            held = line_rows(session, revision)
            tasks = task_lineages(session, revision)
            expected = file_lines(number)
            assert {str(lineage) for lineage in held} == {line["lineage_id"] for line in expected}
            ranks: dict[str, list[tuple[int, int]]] = {}
            for line in expected:
                node, facet = held[UUID(line["lineage_id"])]
                assert node.parent_id is not None
                assert str(tasks[node.parent_id]) == line["task_lineage_id"], line["label"]
                for column, value in facet_of(line).items():
                    assert getattr(facet, column) == value, (line["label"], column)
                ranks.setdefault(line["task_lineage_id"], []).append((line["position"], node.rank))
            for found in ranks.values():
                assert [rank for _, rank in sorted(found)] == list(range(1, len(found) + 1))
    assert [len(file_lines(number)) for number in REVISIONS] == [4997, 4997, 4999]


def test_the_revision_in_progress_holds_the_identifiers_of_the_examples_and_the_marked_ones_theirs(
    witness: Database,
) -> None:
    # A node belongs to one revision: the examples read the identifiers of the revision in
    # progress; a marked one holds the same lineages under identifiers derived from them, none
    # shared, the same on every platform.
    with witness.transaction() as session:
        identifiers = {
            number: {node.id for node, _ in line_rows(session, revision).values()}
            for number, revision in REVISIONS.items()
        }
    in_progress = {line["node_id"] for line in file_lines(102)}
    assert {str(each) for each in identifiers[102]} == in_progress
    assert not identifiers[100] & identifiers[102]
    assert not identifiers[101] & identifiers[102]
    assert not identifiers[100] & identifiers[101]
    assert [len(identifiers[number]) for number in REVISIONS] == [4997, 4997, 4999]


def test_every_line_is_written_by_the_platform_at_the_instant_of_the_event_of_its_revision(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            opened = instant(OPENED[number])
            for node, facet in line_rows(session, revision).values():
                assert (node.created_at, node.created_by) == (opened, None)
                assert (node.updated_at, node.updated_by) == (opened, None)
                assert (facet.created_at, facet.created_by) == (opened, None)
                assert (facet.updated_at, facet.updated_by) == (opened, None)


def test_the_lines_are_priced_at_the_rates_their_revision_keeps_for_their_category(
    witness: Database,
) -> None:
    # The computed is the expected: a labour line costs its quantity of hours at the rate its
    # revision keeps for its category, another line its quantity at its unit disbursement.
    with witness.transaction() as session:
        for revision in REVISIONS.values():
            rates = {
                rate.cost_category_id: rate.amount
                for rate in session.scalars(
                    select(RevisionRate).where(RevisionRate.revision_id == revision)
                )
            }
            for _, facet in line_rows(session, revision).values():
                if facet.resource_role_id is None:
                    assert facet.unit_disbursement is not None
                    product = facet.quantity * facet.unit_disbursement
                else:
                    assert facet.hours is not None
                    product = facet.quantity * facet.hours * rates[facet.cost_category_id]
                assert facet.base_amount == product.quantize(CENT), facet.label


def test_the_update_of_the_rates_is_accepted_on_the_101_at_the_instant_of_its_event(
    witness: Database,
) -> None:
    # Event 6 of the chronology: the two categories of labour take the rates of the reference of
    # 2026 on the 101, a quarter of an hour after its opening; the 100 and the 102 are not asked.
    with witness.transaction() as session:
        rates = {
            number: {
                rate.cost_category_id: (rate.origin, rate.amount)
                for rate in session.scalars(
                    select(RevisionRate).where(RevisionRate.revision_id == revision)
                )
            }
            for number, revision in REVISIONS.items()
        }
        accepted = {each for each, (origin, _) in rates[101].items() if origin == "reference"}
        replayed = session.scalar(
            select(CostStructure.scheduled_at).where(CostStructure.revision_id == REVISION_101)
        )
    assert accepted == RATED
    # The rates of 2026 are above those of 2025 the offer is priced at.
    assert all(rates[101][each][1] > rates[100][each][1] for each in RATED)
    assert instant(RATES_UPDATED).isoformat() == "2026-01-12T10:15:00+00:00"
    # The engine replayed the structure of the 101 at the instant the rates were accepted.
    assert replayed == instant(RATES_UPDATED)


def test_the_labour_lines_of_the_two_categories_cost_more_on_the_101_than_on_the_offer(
    witness: Database,
) -> None:
    # The update raises the rates of the two categories: the same hours, on the same lineage, cost
    # more on the 101 than on the 100, where a line of another category costs the same.
    with witness.transaction() as session:
        offer = line_rows(session, REVISION_100)
        reference = line_rows(session, REVISION_101)
    raised = same = 0
    for lineage, (_, before) in offer.items():
        if lineage not in reference:
            continue
        after = reference[lineage][1]
        if before.hours == after.hours and before.quantity == after.quantity:
            if before.cost_category_id in RATED and before.resource_role_id is not None:
                assert after.base_amount > before.base_amount, before.label
                raised += 1
            else:
                assert after.base_amount == before.base_amount, before.label
                same += 1
    assert raised > 1000
    assert same > 1000


@pytest.mark.requirement("WF-CYC-0030-A")
def test_the_offer_is_designated_the_reference_at_the_order_and_the_project_passes_in_progress(
    logs: Logs, witness_loaded: Database
) -> None:
    # A project whose reference is designated before its code is entered passes In progress at the
    # entry of the code: the designation is made at the instant of event 7 and succeeds, the
    # revision 100 bearing tasks and lines; the transitions say the passage.
    del logs
    with witness_loaded.transaction() as session:
        project = session.get(Project, PRJ_001)
        assert project is not None
        order = instant(ORDER_RECEIVED)
        transitions = [
            (each.from_state, each.to_state, each.occurred_at)
            for each in session.scalars(
                select(ProjectStateTransition)
                .where(ProjectStateTransition.project_id == PRJ_001)
                .order_by(ProjectStateTransition.occurred_at)
            )
        ]
        offer = session.get(Revision, REVISION_100)
        assert offer is not None
        assert (project.state, project.reference_revision_id) == ("in_progress", REVISION_100)
        assert project.current_revision_id == REVISION_102
        assert project.code == "PRJ-001"
        assert (project.inflation_rate, project.win_probability) == (Decimal("0.03"), Decimal(1))
        assert project.order_received_on == date(2026, 1, 15)
        # The last write into the project is the opening of the revision in progress.
        assert project.updated_at == instant(OPENED[102])
        assert offer.is_reference
        assert offer.updated_at == order
    assert transitions == [
        (None, "created", instant(2)),
        ("created", "pricing", instant(OPENED[100])),
        ("pricing", "in_progress", order),
    ]


def test_the_loader_notes_the_designation_it_made(logs: Logs, witness_loaded: Database) -> None:
    del witness_loaded
    noted = logs.named("witness.reference_designated")
    assert [(each["project"], each["revision"]) for each in noted] == [("PRJ-001", 100)]
    assert not logs.named("witness.designation_refused")


def test_the_budgeted_amounts_are_those_of_the_lineage_in_the_reference_the_offer(
    witness: Database,
) -> None:
    # The offer 100 is the reference until the amendment 1 is merged (EP-08): the budgeted amount
    # of a line of the revision in progress, and of the 101, is the re-estimated one of its lineage
    # in the 100, nought without one; the offer reads its own, none being written.
    with witness.transaction() as session:
        offer = line_rows(session, REVISION_100)
        reference = line_rows(session, REVISION_101)
        current = line_rows(session, REVISION_102)
    assert all(facet.budgeted_amount is None for _, facet in offer.values())
    for held in (reference, current):
        for lineage, (_, facet) in held.items():
            before = offer.get(lineage)
            assert facet.budgeted_amount == (
                Decimal("0.00") if before is None else before[1].reestimated_amount
            ), lineage
    assert len(current.keys() - offer.keys()) == 3


def identifying(session: Session) -> dict[int, dict[UUID, dict[str, object]]]:
    """Give what the identifying data of the lines of a revision are, the platform drawing none."""
    return {
        number: {
            lineage: {
                "id": node.id,
                "parent": node.parent_id,
                "rank": node.rank,
                "created_at": node.created_at,
                "updated_at": node.updated_at,
                **{column: getattr(facet, column) for column in facet_of(file_lines(number)[0])},
                "base": facet.base_amount,
                "budgeted": facet.budgeted_amount,
                "reestimated": facet.reestimated_amount,
                "year": facet.consumption_year,
                "lock_version": facet.lock_version,
            }
            for lineage, (node, facet) in line_rows(session, revision).items()
        }
        for number, revision in REVISIONS.items()
    }


def test_two_platforms_loaded_with_the_witness_hold_the_same_lines_and_amounts(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # Identifiers, lineages, places, figures and amounts: the platform draws none of them.
    with witness.transaction() as session:
        first = identifying(session)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    with witness.transaction() as session:
        assert identifying(session) == first
    assert [len(each) for each in first.values()] == [4997, 4997, 4999]


def test_a_second_loading_finds_the_lines_there_and_writes_nothing(
    witness: Database, service_database_url: str
) -> None:
    def counts() -> tuple[int, int]:
        with witness.transaction() as session:
            return (
                session.scalar(select(func.count()).select_from(EstimateLine)) or 0,
                session.scalar(select(func.count()).select_from(Node)) or 0,
            )

    before = counts()
    assert load(service_database_url) == 0
    assert counts() == before
    assert before[0] == 4997 + 4997 + 4999


# --- The reconciliation of the lines of a revision ------------------------------------------------

LATER = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
NEW = UUID("01926f3a-7c00-7000-8000-00000000aaa1")
NEW_LINEAGE = UUID("01926f3a-7c00-7000-8000-00000000aaa2")
MOVED = UUID("01926f3a-7c00-7000-8000-00000000aaa3")


def entry_of(line: dict[str, Any]) -> LineEntry:
    """Give what a line of the file is entered with, every field given."""
    facet = facet_of(line)
    return LineEntry(
        label=str(line["label"]),
        cost_category_id=UUID(line["cost_category_id"]),
        quantity=Decimal(line["quantity"]),
        resource_role_id=facet["resource_role_id"]
        if isinstance(facet["resource_role_id"], UUID)
        else None,
        hours=None if line["hours"] is None else Decimal(line["hours"]),
        unit_disbursement=None
        if line["unit_disbursement"] is None
        else Decimal(line["unit_disbursement"]),
        payment_delay_days=int(line["payment_delay_days"]),
        subproject_id=facet["subproject_id"] if isinstance(facet["subproject_id"], UUID) else None,
        sent=ENTERED,
    )


def load_of(line: dict[str, Any]) -> LineLoad:
    """Give a line of the file, of the revision in progress, as the estimate loads it."""
    entry = entry_of(line)
    return LineLoad(
        UUID(line["node_id"]),
        UUID(line["lineage_id"]),
        UUID(line["task_lineage_id"]),
        line["position"],
        entry,
    )


def test_the_lines_the_copy_gave_are_deleted_changed_and_created_by_lineage(
    witness: Database,
) -> None:
    # Of the 4 999 lines of the revision in progress, the file describes the lines of two tasks: the
    # others are deleted; of those, one is changed in place (its quantity), one is held under
    # another
    # identifier (deleted and written again at the one imposed, its lineage kept), one is created.
    lines = file_lines(102)
    task = next(
        lineage
        for lineage, count in Counter(line["task_lineage_id"] for line in lines).items()
        if count >= 3
    )
    own = [line for line in lines if line["task_lineage_id"] == task]
    other = next(line for line in lines if line["task_lineage_id"] != task)
    assert len(own) >= 3
    kept, changed, renewed = own[0], own[1], own[2]
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
        before = line_rows(session, REVISION_102)
        # The rows are those of the session: what they held before is read before the load.
        counter = before[UUID(changed["lineage_id"])][0].lock_version
        created_before = before[UUID(kept["lineage_id"])][0].created_at
        kept_quantity = before[UUID(kept["lineage_id"])][1].quantity
        total = len(before)
        loads = [
            load_of(kept),
            replace(
                load_of(changed),
                entry=replace(load_of(changed).entry, quantity=Decimal(changed["quantity"]) + 2),
            ),
            replace(load_of(renewed), node_id=MOVED),
            LineLoad(
                NEW,
                NEW_LINEAGE,
                UUID(task),
                len(own) + 1,
                replace(load_of(kept).entry, label="Ligne ajoutée"),
            ),
            load_of(other),
        ]
        act = Act(None, LATER)
        load_lines(session, Place(PRJ_001, REVISION_102, structure), tuple(loads), act)
        session.flush()
        after = line_rows(session, REVISION_102)
        untouched = after[UUID(kept["lineage_id"])]
        modified = after[UUID(changed["lineage_id"])]
        recreated = after[UUID(renewed["lineage_id"])]
        created = after[NEW_LINEAGE]
        # Deleted: every line the file does not describe; created, kept and changed: the five.
        assert set(after) == {
            UUID(kept["lineage_id"]),
            UUID(changed["lineage_id"]),
            UUID(renewed["lineage_id"]),
            NEW_LINEAGE,
            UUID(other["lineage_id"]),
        }
        assert total == 4999
        # Kept: the very same row, not touched but repriced where the dates moved.
        assert untouched[0].id == UUID(kept["node_id"])
        assert untouched[0].created_at == created_before
        assert untouched[1].quantity == kept_quantity
        # Changed: in place, at the counter advanced and the instant imposed, priced again.
        assert modified[1].quantity == Decimal(changed["quantity"]) + 2
        assert modified[0].id == UUID(changed["node_id"])
        assert (modified[1].updated_at, modified[0].updated_at) == (LATER, LATER)
        assert modified[0].lock_version == counter + 1
        # Renewed: the identifier imposed, the lineage kept, written at the instant imposed.
        assert recreated[0].id == MOVED
        assert (recreated[0].created_at, recreated[1].created_at) == (LATER, LATER)
        # Created: at its identifiers, its rank after the lines of its task.
        assert created[0].id == NEW
        assert created[0].lineage_id == NEW_LINEAGE
        assert created[1].label == "Ligne ajoutée"
        # Ranked among the lines the file describes under the task: the three, then it.
        assert created[0].rank == 4
        assert (created[0].created_at, created[0].created_by) == (LATER, None)


def test_a_line_that_names_a_task_the_structure_does_not_hold_stops_the_loading(
    witness: Database,
) -> None:
    line = file_lines(102)[0]
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
        stray = replace(load_of(line), task_lineage_id=UUID(int=7))
        with pytest.raises(ValueError, match="tasks the structure does not hold"):
            load_lines(session, Place(PRJ_001, REVISION_102, structure), (stray,), Act(None, LATER))
