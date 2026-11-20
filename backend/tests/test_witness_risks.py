# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tranche of the risks and the amendments of the witness, loaded and read (US-2650/L1).

``load-witness`` opens the revision 101 by the declaration of the three risks of PRJ-001, each at
its instant, enters their own estimates, enters in the amendment 1 what separates the offer from the
reference, merges it on 1 February, which marks the 101 and makes it the reference, opens the 102
by a review, dismisses 753, makes 752 occur on 20 February, and updates the amendment 2 in the 102
after the last write of its main structure (EP-08, "Le chargeur du témoin").

The rows are those of the witness, identifiers and instants included, and two loadings write the
same; what the service reads of them is compared with the examples of the contract, but for what
the slice does not reach, listed here (``UNREACHED``), each with its cause.
"""

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from installed_reference import install
from projects_support import MANAGING, PROJECTS, contribute, person
from sqlalchemy import select
from test_witness import load, wipe
from test_witness_lines_reads import deviations
from test_witness_projects import REVISION_100, REVISION_101, REVISION_102, keyed, without
from witness_support import PRJ_001, example

from waterfall.core.planning.tables import Node
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

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

# What the slice does not reach, by reading: the fields of an example the loaded witness differs
# from, each with its cause.
COUNTER = "the counter follows the writes of the loading, one by node and by line entered"
UNREACHED = {
    "risk": {"lock_version": COUNTER},
    "structure": {"lock_version": COUNTER},
    "report": {
        "main_structure_lock_version": COUNTER,
        "amendment_lock_version": COUNTER,
        "risk_lock_version": COUNTER,
    },
}


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
        risks = {row.id: row for row in session.scalars(select(Risk))}
        evaluations = {
            (row.risk_id, row.revision_id): row for row in session.scalars(select(RiskEvaluation))
        }
        reviews = sorted(
            (row.risk_id, row.created_at, row.state, row.revision_id)
            for row in session.scalars(select(RiskReview))
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


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_occurrence_grafts_the_own_estimate_of_752_under_the_identifiers_of_the_examples(
    witness: Database,
) -> None:
    grafted = {
        each["node_id"]: each["lineage_id"] for each in example("nodes_risk_occurred")["items"]
    }
    with witness.transaction() as session:
        nodes = {
            str(row.id): row
            for row in session.scalars(
                select(Node).where(Node.structure_id == MAIN_102, Node.origin_risk_id == DELAY)
            )
        }
    assert {each: str(row.lineage_id) for each, row in nodes.items()} == grafted
    assert {row.structure_id for row in nodes.values()} == {MAIN_102}
    assert {row.created_at for row in nodes.values()} == {OCCURRED}


def identifying(database: Database) -> dict[str, list[tuple[str, ...]]]:
    """Give what identifies the risks, the structures, the reviews and the nodes of the witness."""
    with database.transaction() as session:
        return {
            "risk": sorted(
                (str(row.id), row.label, str(row.created_at))
                for row in session.scalars(select(Risk))
            ),
            "review": sorted(
                (str(row.id), str(row.risk_id), str(row.revision_id), str(row.created_at))
                for row in session.scalars(select(RiskReview))
            ),
            "evaluation": sorted(
                (str(row.risk_id), str(row.revision_id), str(row.provision_node_id))
                for row in session.scalars(select(RiskEvaluation))
            ),
            "structure": sorted(
                (str(row.id), str(row.revision_id), row.kind, str(row.lineage_id))
                for row in session.scalars(select(CostStructure))
            ),
            "node": sorted(
                (str(row.id), str(row.structure_id), str(row.lineage_id), str(row.parent_id))
                for row in session.scalars(select(Node))
            ),
        }


@pytest.mark.requirement("WF-QUA-0040-A")
def test_two_loadings_give_the_same_risks_structures_reviews_and_lines_identifiers_included(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # Every identifier, those no example names included: the loader draws them in order.
    first = identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying(witness) == first
    assert len(first["risk"]) == 3
    assert len({row[1] for row in first["node"]}) == len(first["structure"])


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_labels_of_the_risks_and_of_the_amendments_are_those_of_the_witness(
    witness: Database,
) -> None:
    described = {each["label"] for each in example("witness_risks")["risks"]}
    amendments = {each["label"] for each in example("witness_structures")["amendments"]}
    with witness.transaction() as session:
        labels = set(session.scalars(select(Risk.label)))
        kinds = {
            row.label
            for row in session.scalars(
                select(CostStructure).where(CostStructure.kind.in_(("amendment", "risk")))
            )
        }
    assert labels == described
    assert kinds == described | amendments


def compared(ours: Any, theirs: Any, unreached: set[str]) -> tuple[Any, Any]:
    """Give a reading and its example without the fields the slice does not reach."""
    return without(ours, unreached), without(theirs, unreached)


@pytest.mark.story("US-2650")
def test_the_register_the_risk_and_the_matrix_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    read = managing(api, witness, realm)
    unreached = set(UNREACHED["risk"])
    ours, theirs = compared(read(f"{BASE}/risks"), example("risks"), unreached)
    assert ours == theirs
    ours, theirs = compared(read(f"{BASE}/risks/{REWORK}"), example("risk"), unreached)
    assert ours == theirs
    ours, theirs = compared(
        read(f"{BASE}/risks/{DELAY}"), example("risk_occurred_detail"), unreached
    )
    assert ours == theirs
    assert read(f"{BASE}/risks/matrix") == example("risk_matrix")


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


@pytest.mark.story("US-2650")
def test_the_structures_of_the_101_and_of_the_102_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # In the order of their labels, after the main structure, which the contract does not fix:
    # compared by identifier.
    read = managing(api, witness, realm)
    unreached = set(UNREACHED["structure"])
    for revision, name in ((REVISION_102, "structures"), (REVISION_101, "structures_amendments")):
        listed = cast("list[dict[str, Any]]", read(f"{BASE}/revisions/{revision}/structures"))
        body = keyed(listed, "structure_id")
        expected = keyed(example(name), "structure_id")
        assert body.keys() == expected.keys()
        for identifier, item in body.items():
            ours, theirs = compared(item, expected[identifier], unreached)
            assert ours == theirs, identifier


PROVISION = "Provision — "


def labelled(text: str) -> str:
    """Give a label as both sides write it: a provision line without its first case (#4275)."""
    if not text.startswith(PROVISION):
        return text
    named = text.removeprefix(PROVISION)
    return PROVISION + named[:1].lower() + named[1:]


def described(difference: dict[str, Any]) -> str:
    """Give a difference of a report as what it says, in any order."""
    return json.dumps({**difference, "label": labelled(difference["label"])}, sort_keys=True)


@pytest.mark.story("US-2650")
def test_the_reports_of_the_merge_and_of_the_occurrence_read_are_the_examples(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The merge of the amendment 2 and the occurrence of 751, as the reader who would confirm them
    # reads them today. The examples lack what #4276 names: the link of the task the amendment adds
    # and the order of the report; the tasks the graft redates (#4134), the provision and the start
    # of the own estimate (#4133).
    read = managing(api, witness, realm)
    unreached = {*UNREACHED["report"], "differences"}
    merge = read(f"{BASE}/revisions/{REVISION_102}/structures/{AMENDMENT_2}/merge")
    expected = example("structure_merge_report")
    ours, theirs = compared(merge, expected, unreached)
    assert ours == theirs
    wanted = {described(each) for each in expected["differences"]}
    extra = [each for each in merge["differences"] if described(each) not in wanted]
    assert [(each["change"], each["label"], each["predecessor_label"]) for each in extra] == [
        ("added", "Reprise des essais de câblage", "Montage des armoires sur site")
    ]
    assert wanted <= {described(each) for each in merge["differences"]}
    occurrence = read(f"{BASE}/risks/{REWORK}/occurrence")
    expected = example("risk_occurrence_report")
    unreached |= {"provision_amount", "own_estimate_past_planning_start_on"}
    ours, theirs = compared(occurrence, expected, unreached)
    assert ours == theirs
    wanted = {described(each) for each in expected["differences"]}
    redated = [each for each in occurrence["differences"] if described(each) not in wanted]
    assert {(each["change"], each["target"]) for each in redated} == {("updated", "task")}
    assert wanted <= {described(each) for each in occurrence["differences"]}
    assert len(occurrence["differences"]) == len(wanted) + len(redated)
    assert occurrence["own_estimate_past_planning_start_on"] == "2026-01-12"


# What the own estimate of a risk reads otherwise than the examples (#4278): the budgeted amount of
# its lines, nought where the examples read their amount, what follows from it, and the previous
# figures the 101 gives the 102, which the examples do not; the counters and the instant the engine
# dated the structure follow the writes of the loading, and the service names the default calendar
# the examples leave out, as for the tasks of the main structure (``test_witness_tasks``).
OWN_ESTIMATE_APART = {
    "/meta/scheduled_at",
    "/items[]/task/calendar_id",
    "/items[]/lock_version",
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


# The own estimates the examples read: of 751 in the 102, of 752 in the 101 that froze it.
OWN_ESTIMATES = {
    "nodes_risk_estimate": (REVISION_102, OWN_102[REWORK]),
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
    assert [each["node_id"] for each in body["items"]] == [
        each["node_id"] for each in expected["items"]
    ]
    assert deviations(body, expected) <= OWN_ESTIMATE_APART
