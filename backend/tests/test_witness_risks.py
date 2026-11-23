# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tranche of the risks and the amendments of the witness, loaded and read (US-2650/L1).

``load-witness`` opens the revision 101 by the declaration of the three risks of PRJ-001, each at
its instant, enters their own estimates, enters in the amendment 1 what separates the offer from the
reference, merges it on 1 February, which marks the 101 and makes it the reference, opens the 102
by a review, dismisses 753, makes 752 occur on 20 February, and updates the amendment 2 in the 102
after the last write of its main structure (EP-08, "Le chargeur du témoin").

The rows are those of the witness, identifiers and instants included, and two loadings write the
same; what the service reads of them is compared with the examples of the contract, counters
included: where the two disagree, the specification arbitrates and the example is corrected.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from installed_reference import install
from projects_support import MANAGING, PROJECTS, contribute, person
from sqlalchemy import select
from test_witness import load, wipe
from test_witness_lines_reads import deviations
from test_witness_portfolio import identifying as slice_identifying
from test_witness_projects import REVISION_100, REVISION_101, REVISION_102, keyed, without
from witness_support import PRJ_001, example

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, TaskLink, TrackingEntry
from waterfall.core.planning.tables import Task as TaskFacet
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient, Logs

    from waterfall.platform.database import Database

BASE = f"{PROJECTS}/{PRJ_001}"
UNIVERSE = "01926f3a-7c00-7000-8000-000000000"
REWORK, DELAY, AUTOMATION = (UUID(f"{UNIVERSE}{number}") for number in (751, 752, 753))
MAIN_101, AMENDMENT_1, AMENDMENT_2_IN_101 = (UUID(f"{UNIVERSE}{n}") for n in (211, 212, 213))
OWN_101 = {REWORK: UUID(f"{UNIVERSE}214"), DELAY: UUID(f"{UNIVERSE}215")}
MAIN_102, AMENDMENT_2 = UUID(f"{UNIVERSE}201"), UUID(f"{UNIVERSE}203")
OWN_102 = {
    REWORK: UUID(f"{UNIVERSE}204"),
    DELAY: UUID(f"{UNIVERSE}205"),
    AUTOMATION: UUID(f"{UNIVERSE}206"),
}


def at(day: date, hour: int, minute: int = 0) -> datetime:
    """Give an instant of the chronology, in universal time."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)


IDENTIFIED_ON = date(2026, 1, 12)
DECLARED = {
    REWORK: at(IDENTIFIED_ON, 10),
    DELAY: at(IDENTIFIED_ON, 10, 30),
    AUTOMATION: at(IDENTIFIED_ON, 11),
}
MERGED = at(date(2026, 2, 1), 9)
REVIEWED = at(date(2026, 2, 2), 9)
DISMISSED = at(date(2026, 2, 2), 14)
OCCURRED = at(date(2026, 2, 20), 16)
STUDIES = at(date(2026, 3, 2), 9, 15)


def managing(api: ContractClient, witness: Database, realm: TestRealm) -> Any:
    """Give a reader of PRJ-001 that manages it, who reads the commands the examples list."""
    who = person(witness, realm, *MANAGING)
    contribute(witness, str(PRJ_001), who, "project_manager")

    def read(url: str) -> Any:
        answer = api.get(url, headers=who.headers)
        assert answer.status_code == 200, answer.text
        return answer.json()

    return read


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_three_risks_are_declared_with_the_identifiers_and_at_the_instants_of_the_witness(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        risks = {
            row.id: row for row in session.scalars(select(Risk).where(Risk.project_id == PRJ_001))
        }
        evaluations = {
            (row.risk_id, row.revision_id): row
            for row in session.scalars(
                select(RiskEvaluation).where(RiskEvaluation.project_id == PRJ_001)
            )
        }
        reviews = sorted(
            (row.risk_id, row.created_at, row.state, row.revision_id)
            for row in session.scalars(select(RiskReview).where(RiskReview.project_id == PRJ_001))
        )
    assert {each: row.created_at for each, row in risks.items()} == DECLARED
    # Each declared, then reviewed as its own estimate is entered, the same instant; 751 reviewed
    # at the opening of the 102 and at the start of the studies, 753 dismissed, 752 occurred.
    assert reviews == sorted(
        [
            *((risk, instant, "identified", REVISION_101) for risk, instant in DECLARED.items()),
            *((risk, instant, "identified", REVISION_101) for risk, instant in DECLARED.items()),
            (REWORK, REVIEWED, "identified", REVISION_102),
            (REWORK, STUDIES, "identified", REVISION_102),
            (AUTOMATION, DISMISSED, "dismissed", REVISION_102),
            (DELAY, OCCURRED, "occurred", REVISION_102),
        ]
    )
    assert {key: row.structure_id for key, row in evaluations.items()} == {
        **{(risk, REVISION_101): structure for risk, structure in OWN_101.items()},
        (AUTOMATION, REVISION_101): UUID(f"{UNIVERSE}216"),
        **{(risk, REVISION_102): structure for risk, structure in OWN_102.items()},
    }
    # The provision lines of the 101 bear the lineage the 102 copies them under: 555 for 751, the
    # one still identified; 752 occurred and 753 dismissed lost theirs.
    assert evaluations[REWORK, REVISION_101].provision_node_id == UUID(f"{UNIVERSE}655")
    assert evaluations[REWORK, REVISION_102].provision_node_id == UUID(f"{UNIVERSE}555")
    assert {evaluations[risk, REVISION_102].state for risk in (DELAY, AUTOMATION)} == {
        "occurred",
        "dismissed",
    }


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_101_is_opened_by_the_risks_and_marked_the_reference_by_the_merge_of_the_amendment_1(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        revisions = {row.id: row for row in session.scalars(select(Revision))}
        project = session.get_one(Project, PRJ_001)
        structures = {
            row.id: row
            for row in session.scalars(select(CostStructure).where(CostStructure.kind != "base"))
        }
    reference = revisions[REVISION_101]
    assert (reference.created_at, reference.marked_at) == (DECLARED[REWORK], MERGED)
    assert reference.is_reference
    assert not revisions[REVISION_100].is_reference
    assert project.reference_revision_id == REVISION_101
    assert revisions[REVISION_102].created_at == REVIEWED
    in_101 = {each for each, row in structures.items() if row.revision_id == REVISION_101}
    in_102 = {each for each, row in structures.items() if row.revision_id == REVISION_102}
    assert in_101 == {MAIN_101, AMENDMENT_1, AMENDMENT_2_IN_101, *OWN_101.values()} | {
        UUID(f"{UNIVERSE}216")
    }
    assert in_102 == {MAIN_102, AMENDMENT_2, *OWN_102.values()}
    # The amendment 1 merged, the amendment 2 not; taken over by the 102 and updated there.
    assert structures[AMENDMENT_1].is_merged
    assert not structures[AMENDMENT_2].is_merged
    assert structures[AMENDMENT_2].main_lock_version == structures[MAIN_102].lock_version
    assert structures[OWN_102[DELAY]].is_merged


@pytest.mark.story("US-3070")
def test_the_loading_copies_an_own_estimate_again_only_where_the_main_structure_moved_past_it(
    logs: Logs, witness_logged: Database
) -> None:
    # Each copy again of the main structure into an own estimate and its base costs two structures
    # as large as the main one, some seven seconds of the loading on a workstation: the loader
    # does it once by revision opened and by risk it enters there, and before an occurrence — the
    # 751 in the 102 opened, the 752 before it occurs —, never for an own estimate declared whole.
    del witness_logged  # asked for its side effect: the records of the loading, in ``logs``
    assert logs.named("witness.loaded"), "the records of the loading do not say it loaded"
    copied = logs.named("witness.own_estimate_copied_again")
    assert [(UUID(each["risk"]), each["revision"]) for each in copied] == [
        (REWORK, 102),
        (DELAY, 102),
    ]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_occurrence_merges_the_own_estimate_of_752_into_the_main_structure_of_the_102(
    witness: Database,
) -> None:
    # The nodes the examples read, by their label. Their identifiers and their lineages are those
    # of the graft of EP-08: the occurrence merges the own estimate since US-3070/L3, under the
    # lineages it holds there and identifiers drawn, which the loader of US-3150/L1 (#4614) imposes
    # again — the declared deviation of the examples until then.
    described = {
        (each.get("task") or each["estimate_line"])["label"]
        for each in example("nodes_risk_occurred")["items"]
    }
    with witness.transaction() as session:
        nodes = session.scalars(
            select(Node).where(Node.structure_id == MAIN_102, Node.origin_risk_id == DELAY)
        ).all()
        labels = {
            *session.scalars(
                select(TaskFacet.label).where(TaskFacet.node_id.in_([row.id for row in nodes]))
            ),
            *session.scalars(
                select(EstimateLine.label).where(
                    EstimateLine.node_id.in_([row.id for row in nodes])
                )
            ),
        }
    assert labels == described
    assert len(nodes) == len(described)
    assert {row.structure_id for row in nodes} == {MAIN_102}
    assert {row.created_at for row in nodes} == {OCCURRED}


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give, for what the witness holds, each identifier with its natural key.

    The risks, their reviews and evaluations, the structures, the nodes and their facets — the
    tasks, the estimate lines, the inscriptions —, the links, and the history: what the journal
    records of the project. A pair, never an identifier alone: two loadings that drew the same
    identifiers for other rows would not be told apart.
    """
    with database.transaction() as session:
        return {
            "risk": sorted(
                (row.id, row.label, row.created_at) for row in session.scalars(select(Risk))
            ),
            "review": sorted(
                (row.id, row.risk_id, row.revision_id, row.created_at, row.state, row.severity)
                for row in session.scalars(select(RiskReview))
            ),
            "evaluation": sorted(
                (row.risk_id, row.revision_id, row.structure_id, row.provision_node_id)
                for row in session.scalars(select(RiskEvaluation))
            ),
            "structure": sorted(
                (row.id, row.revision_id, row.kind, row.lineage_id, row.label)
                for row in session.scalars(select(CostStructure))
            ),
            "node": sorted(
                (row.id, row.structure_id, row.lineage_id, row.kind, row.parent_id, row.rank)
                for row in session.scalars(select(Node))
            ),
            "task": sorted(
                (
                    row.node_id,
                    row.label,
                    row.scheduling_mode,
                    row.duration_value,
                    row.start_date,
                    row.finish_date,
                )
                for row in session.scalars(select(TaskFacet))
            ),
            "link": sorted(
                (
                    row.id,
                    row.structure_id,
                    row.predecessor_id,
                    row.successor_id,
                    row.link_type,
                    row.lag_value,
                )
                for row in session.scalars(select(TaskLink))
            ),
            "estimate_line": sorted(
                (row.node_id, row.label, row.quantity, row.hours, row.base_amount)
                for row in session.scalars(select(EstimateLine))
            ),
            "inscription": sorted(
                (row.id, row.lineage_id, row.kind, row.timeline_id)
                for row in session.scalars(select(TrackingEntry))
            ),
            "history": sorted(
                (row.id, row.occurred_at, row.action, row.object_kind, row.object_id)
                for row in session.scalars(select(AuditEntry))
            ),
        }


@pytest.mark.requirement("WF-QUA-0040-A")
def test_two_loadings_give_the_same_identifiers_with_their_natural_keys(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # Every identifier, those no example names included: the loader draws them in order. The risks
    # and their reviews, the structures, the nodes with their tasks and lines, the links, the
    # inscriptions and the history, each identifier with what it names.
    first, slice_first = identifying(witness), slice_identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    second = identifying(witness)
    # « Deux engendrements successifs donnent des données identifiantes identiques. » for the slice
    # of the portfolio (EP-11, US-2770): the same second loading, a full one costing minutes.
    assert slice_identifying(witness) == slice_first
    assert len(slice_first["project"]) == 10
    assert slice_first["node"]
    assert slice_first["cost_line"]
    assert second.keys() == first.keys()
    for name, rows in first.items():
        assert second[name] == rows, name
        assert rows, name
    # The three risks of PRJ-001, and the four of the slice of the portfolio.
    assert len(first["risk"]) == 3 + 4
    assert len({row[1] for row in first["node"]}) == len(first["structure"])


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_labels_of_the_risks_and_of_the_amendments_are_those_of_the_witness(
    witness: Database,
) -> None:
    described = {each["label"] for each in example("witness_risks")["risks"]}
    amendments = {each["label"] for each in example("witness_structures")["amendments"]}
    with witness.transaction() as session:
        labels = set(session.scalars(select(Risk.label).where(Risk.project_id == PRJ_001)))
        kinds = {
            row.label
            for row in session.scalars(
                select(CostStructure).where(
                    CostStructure.kind.in_(("amendment", "risk")),
                    CostStructure.project_id == PRJ_001,
                )
            )
        }
    assert labels == described
    assert kinds == described | amendments


# What the examples say of a risk that the service does not serve yet: EP-30 writes into the
# contract the trend of a risk and the severity of an occurred risk read at its cost at occurrence,
# which its computed fields name (US-3080/L1, #4589). Each exemption is lifted by the lot that
# serves it: `trend` by US-3160/L1 (#4598), the severity of an occurred risk and its
# `computed_fields` by US-3080/L2 (#4590). Lifting one fails `test_the_trend_is_not_served_yet`.
RISK_APART = frozenset({"trend"})
OCCURRED_APART = RISK_APART | {"computed_fields"}


def served_risk(risk: dict[str, Any]) -> dict[str, Any]:
    """Give what the service serves of a risk, the fields it does not serve yet set apart."""
    apart = OCCURRED_APART if risk["state"] == "occurred" else RISK_APART
    return {key: value for key, value in risk.items() if key not in apart}


# The risks whose counter the loader advances beyond the examples: it carries the main structure
# into their own estimates by copying it again, then adds what they designate (``enter_estimate``),
# two writes where the update of US-3090 makes one — at the opening of the 102 for 751, before its
# occurrence for 752. The declared deviation of US-3070/L3, which US-3150/L1 (#4614) lifts by the
# update; their severities and their provisions are the examples'.
COUNTED_APART = {str(REWORK), str(DELAY)}


def uncounted(risk: dict[str, Any]) -> dict[str, Any]:
    """Give ``served_risk``, the counter of a risk of ``COUNTED_APART`` set apart."""
    served = served_risk(risk)
    if risk["risk_id"] in COUNTED_APART:
        del served["lock_version"]
    return served


@pytest.mark.story("US-2650")
def test_the_register_the_risk_and_the_matrix_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    read = managing(api, witness, realm)
    register, expected = read(f"{BASE}/risks"), example("risks")
    assert without(register, {"items"}) == without(expected, {"items"})
    assert [uncounted(each) for each in register["items"]] == [
        uncounted(each) for each in expected["items"]
    ]
    counters = zip(register["items"], expected["items"], strict=True)
    moved = {
        ours["risk_id"]
        for ours, theirs in counters
        if ours["lock_version"] != theirs["lock_version"]
    }
    assert moved == COUNTED_APART
    assert uncounted(read(f"{BASE}/risks/{REWORK}")) == uncounted(example("risk"))
    occurred = read(f"{BASE}/risks/{DELAY}")
    assert uncounted(occurred) == uncounted(example("risk_occurred_detail"))
    assert read(f"{BASE}/risks/matrix") == example("risk_matrix")
    # The exemption of `trend` ends with US-3160/L1 (#4598): remove it from RISK_APART then.
    assert not any("trend" in each for each in (*register["items"], occurred))


@pytest.mark.story("US-2650")
def test_the_reviews_and_the_coverage_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    read = managing(api, witness, realm)
    assert read(f"{BASE}/risks/{REWORK}/reviews") == example("risk_reviews")
    # The coverage is computed at the reading, today: the instant of the example is the day the
    # examples are read at.
    coverage = read(f"{BASE}/risks/coverage")
    expected = example("risk_coverage")
    assert without(coverage, {"computed_at"}) == without(expected, {"computed_at"})


# What the examples say of the own estimate of a risk that the service does not serve yet: EP-30
# writes into the contract the state of an own estimate, whole or pruned and up to date, its date,
# which is the main structure's, and its update (US-3070/L2, #4585); the service says them from
# US-3070/L3 and US-3090, which take this set apart back.
OWN_STRUCTURE_APART = frozenset(
    {"is_up_to_date", "is_pruned", "planning_start_on", "available_commands"}
)


def served(structure: dict[str, Any]) -> dict[str, Any]:
    """Give what the service serves of a structure today, the state of an own estimate set apart."""
    apart = OWN_STRUCTURE_APART if structure["kind"] == "risk" else {"is_pruned"}
    return {key: value for key, value in structure.items() if key not in apart}


# The structures whose counter the loading advances beyond the examples. The severity is recorded at
# each write of an own estimate (EP-30): the loader fills them in steps — the copy of the main
# structure, then the tasks, then the lines they designate, the copy made again before the 102 and
# before the occurrence of 752 (``COUNTED_APART``) —, and the provision line, which reaches the
# amount of the examples at the end, moves at each step, advancing the main structure that bears it,
# in the 101 as in the 102, where the merge of the occurrence of 752 writes it otherwise than the
# graft of EP-08; the own estimates of 751 in the 101 and of 752 in the 102 count the writes of
# their steps. The declared deviation of US-3070/L3, which US-3150/L1 (#4614) lifts by the update.
STRUCTURES_COUNTED_APART = {
    str(MAIN_101),
    str(MAIN_102),
    str(OWN_101[REWORK]),
    str(OWN_102[DELAY]),
}


@pytest.mark.story("US-2650")
def test_the_structures_of_the_101_and_of_the_102_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # In the order of their labels, after the main structure, which the contract does not fix:
    # compared by identifier.
    read = managing(api, witness, realm)
    for revision, name in ((REVISION_102, "structures"), (REVISION_101, "structures_amendments")):
        listed = cast("list[dict[str, Any]]", read(f"{BASE}/revisions/{revision}/structures"))
        body = keyed(listed, "structure_id")
        expected = keyed(example(name), "structure_id")
        assert body.keys() == expected.keys()
        for identifier, item in body.items():
            ours, theirs = served(item), served(expected[identifier])
            if identifier in STRUCTURES_COUNTED_APART:
                assert ours.pop("lock_version") != theirs.pop("lock_version"), identifier
            assert ours == theirs, identifier


@pytest.mark.story("US-2650")
def test_the_reports_of_the_merge_and_of_the_occurrence_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The merge of the amendment 2 and the occurrence of 751, as the reader who would confirm them
    # reads them today: the differences in the order of the service, the counters.
    read = managing(api, witness, realm)
    merge = read(f"{BASE}/revisions/{REVISION_102}/structures/{AMENDMENT_2}/merge")
    expected = example("structure_merge_report")
    # The nodes the occurrence of 752 adds, which the amendment 2 holds under the lineages the
    # examples give them and the main structure under those of the own estimate, and the counter of
    # the main structure (``STRUCTURES_COUNTED_APART``): the declared deviation of US-3070/L3, which
    # US-3150/L1 (#4614) lifts.
    occurred = {
        (each.get("task") or each["estimate_line"])["label"]
        for each in example("nodes_risk_occurred")["items"]
    }
    kept = [each for each in merge["differences"] if each["label"] not in occurred]
    assert {each["label"] for each in merge["differences"]} - {e["label"] for e in kept} == occurred
    apart = {"differences", "main_structure_lock_version"}
    assert without(merge, apart) == without(expected, apart)
    assert kept == expected["differences"]
    # The report of the occurrence of 751 is the merge's of its own estimate since US-3070/L3, the
    # example still the graft's of EP-08: the start of the own estimate is the main structure's, the
    # tasks the graft redated and the provision line it removed are not among its differences, and
    # its counters are those of ``COUNTED_APART``. The declared deviation of US-3070/L3, which
    # US-3100/L2 (#4592) and US-3150/L1 (#4614) lift; what the own estimate adds is the example's.
    occurrence = read(f"{BASE}/risks/{REWORK}/occurrence")
    described = example("risk_occurrence_report")
    report_apart = {
        "differences",
        "main_structure_lock_version",
        "risk_lock_version",
        "own_estimate_past_planning_start_on",
    }
    assert without(occurrence, report_apart) == without(described, report_apart)
    assert occurrence["own_estimate_past_planning_start_on"] == "2026-03-02"
    assert occurrence["completed_provision_task"] is None
    assert added(occurrence) == added(described)


def added(report: dict[str, Any]) -> set[tuple[str, str]]:
    """Give the tasks and the lines a report adds, by their label."""
    return {
        (each["target"], each["label"])
        for each in report["differences"]
        if each["change"] == "added" and each["target"] != "link"
    }


# What the own estimate of a risk reads otherwise than the examples (#4278): the budgeted amount of
# its lines, nought where the examples read their amount, what follows from it, and the previous
# figures the 101 gives the 102, which the examples do not; the instant the engine dated the
# structure follows the writes of the loading, and the service names the default calendar the
# examples leave out, as for the tasks of the main structure (``test_witness_tasks``).
OWN_ESTIMATE_APART = {
    "/meta/scheduled_at",
    "/items[]/task/calendar_id",
    "/items[]/task/budgeted_amount",
    "/items[]/task/physical_progress/is_computable",
    "/items[]/task/physical_progress/reason",
    "/items[]/task/physical_progress/value",
    "/items[]/estimate_line/budgeted_amount",
    "/items[]/estimate_line/previous_quantity",
    "/items[]/estimate_line/previous_reestimated_amount",
    "/items[]/estimate_line/previous_unit_disbursement",
    "/totals/budgeted_amount",
}


# What the own estimate of 752 in the 101 reads otherwise than the example, whole: the copy of the
# main structure (EP-30), to which it adds its nodes at the first level, after those of the main
# structure, read against its base, which tells them added; their float and their criticality are
# those of the whole plan, its totals and its depth the project's. Its pruning at the marking, which
# leaves it what it designates, is US-3070/L4's (#4587): the declared deviation of US-3070/L3, the
# nodes the example reads compared among those it holds.
WHOLE_APART = {
    "/meta/summary_depth",
    "/items[]/difference",
    "/items[]/row_number",
    "/items[]/position",
    "/items[]/predecessors[]/predecessor_row_number",
    "/items[]/task/total_float/value",
    "/items[]/task/is_critical",
    "/totals/task_count",
    "/totals/estimate_line_count",
    "/totals/hours",
    "/totals/base_amount",
    "/totals/budgeted_amount",
    "/totals/reestimated_amount",
}


# The own estimates the examples read: of 752 in the 101 that froze it. That of 751 in the 102,
# ``nodes_risk_estimate``, is read as a differential of the main structure since EP-30
# (US-3070/L2, #4585), which the loader of the witness loads so from US-3150.
OWN_ESTIMATES = {
    "nodes_risk_estimate_occurred": (REVISION_101, OWN_101[DELAY]),
}


@pytest.mark.story("US-2650")
@pytest.mark.parametrize("name", list(OWN_ESTIMATES))
def test_the_own_estimates_read_are_the_examples_but_for_their_budget(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    # The own estimate of 751 in the 102, of 752 in the 101 that froze it before its occurrence:
    # the same nodes under the same identifiers, the same tasks, lines and amounts.
    read = managing(api, witness, realm)
    revision, structure = OWN_ESTIMATES[name]
    body = read(f"{BASE}/revisions/{revision}/structures/{structure}/nodes")
    expected = example(name)
    wanted = [each["node_id"] for each in expected["items"]]
    # The nodes the example reads, in its order, among those the whole copy holds.
    assert [each["node_id"] for each in body["items"] if each["node_id"] in wanted] == wanted
    held = keyed(body["items"], "node_id")
    designated = {**body, "items": [held[node_id] for node_id in wanted]}
    assert deviations(designated, expected) <= OWN_ESTIMATE_APART | WHOLE_APART
