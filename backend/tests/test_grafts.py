# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The graft of an own estimate into the main structure, by the planning (``graft``).

US-2620/L1. What the occurrence of a risk writes (WF-RIS-0060), the graft applied in the
transaction of the worker as US-2620/L2 will call it — the evaluation of the risk made occurred
first, which releases its provision line —, then read through the service: the tasks of the own
estimate placed, in their order, last under the task that bore the provision, with their
subordinates, their links, their durations and their modes, a leaf without predecessor in manual
mode at its dates; after a milestone, which stays one; the lines at a budgeted amount of nought and
their re-estimated amount, the provision line removed, the total of the task bearing it moved by
their amount less the provision; each node marked with its risk; what the report said, written; a
graft refused by its first reason writing nothing.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from occurrence_support import (
    DIAGNOSTIC,
    REWIRING,
    REWORK,
    SEARCH,
    TESTS,
    WIRES,
    Occurring,
    idle_diagnostic,
    main_task,
    occurring,
)
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed
from sqlalchemy import delete, select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import Graft, Grafted, graft
from waterfall.core.planning.tables import Node, Task
from waterfall.core.risks.tables import RiskEvaluation
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The tasks of the own estimate, by their label, and the lines, by theirs, with their amounts.
GRAFTED_TASKS = (DIAGNOSTIC, REWORK, REWIRING, TESTS)
GRAFTED_LINES = {SEARCH: "120.00", WIRES: "80.00"}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def ready(api: ContractClient, project: Costed) -> Occurring:
    """Give the risk identified in the second revision, its own estimate filled, autonomous.

    The own estimate is a copy of the main structure since EP-30 (US-3070/L3), which the graft
    would copy whole: the copies of the nodes of the main structure are taken out of it around the
    service, leaving what it adds alone, as the own estimate of EP-08 the graft was written for. The
    occurrence no longer grafts; US-3100/L3 retires the graft and these tests.
    """
    ready = occurring(api, project)
    own = UUID(ready.read()["structure_id"])
    main = UUID(ready.main_structure()["structure_id"])
    with project.stage.owner.begin() as connection:
        copies = select(Node.id).where(
            Node.structure_id == own,
            Node.lineage_id.in_(select(Node.lineage_id).where(Node.structure_id == main)),
        )
        held = list(connection.scalars(copies))
        connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(held)))
        connection.execute(delete(Task).where(Task.node_id.in_(held)))
        lines = select(Node.id).where(Node.id.in_(held), Node.kind == "estimate_line")
        connection.execute(delete(Node).where(Node.id.in_(lines)))
        connection.execute(delete(Node).where(Node.id.in_(held)))
    return ready


def _asked(ready: Occurring, bearer: str | None = None) -> Graft:
    """Give the graft of the own estimate of the risk under the task bearing its provision."""
    risk = ready.read()
    line = risk["provision_node_id"]
    held = next(each for each in ready.main() if each["node_id"] == line)
    return Graft(
        ready.project.project_id,
        UUID(risk["structure_id"]),
        UUID(ready.main_structure()["structure_id"]),
        UUID(bearer or held["parent_id"]),
        (UUID(line),),
        UUID(risk["risk_id"]),
    )


def _grafted(ready: Occurring, asked: Graft, *, applied: bool = True) -> Grafted:
    """Graft as the worker will, the risk made occurred first; or compute it alone."""
    with ready.project.stage.database.transaction() as session:
        if not applied:
            return graft(session, asked)
        session.execute(
            update(RiskEvaluation)
            .where(
                RiskEvaluation.risk_id == asked.origin_risk_id,
                RiskEvaluation.revision_id == UUID(ready.revision["revision_id"]),
            )
            .values(state="occurred", provision_node_id=None, occurrence_cost=Decimal(200))
        )
        return graft(session, asked, Act(None, utc_now()))


def _by_label(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index the nodes of a structure by their label, a task's or a line's."""
    return {(each.get("task") or each["estimate_line"])["label"]: each for each in nodes}


def _children(nodes: list[dict[str, Any]], parent: str | None) -> list[str]:
    """Give the labels of the subtasks of a task, in their order — the first level for none."""
    return [
        each["task"]["label"]
        for each in nodes
        if each["kind"] == "task" and each["parent_id"] == parent
    ]


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_tasks_grafted_go_last_under_the_bearer_with_their_plan_kept(
    ready: Occurring,
) -> None:
    # The diagnostic, without predecessor, manual at the dates of the own estimate; the rework a
    # summary over the rewiring and the tests, which keep their links, their durations and their
    # automatic mode, and their dates — the planning start of the main structure, a week earlier,
    # moves none of them. ``Étude`` bears them last, a summary now.
    own = _by_label(ready.own())
    _grafted(ready, _asked(ready))
    main = ready.main()
    held = _by_label(main)
    study = held[STUDY]
    assert _children(main, study["node_id"]) == [DIAGNOSTIC, REWORK]
    assert _children(main, held[REWORK]["node_id"]) == [REWIRING, TESTS]
    assert study["task"]["is_summary"] is True
    for label in GRAFTED_TASKS:
        task, source = held[label]["task"], own[label]["task"]
        assert (task["duration"], task["start"], task["finish"]) == (
            source["duration"],
            source["start"],
            source["finish"],
        )
    modes = {label: held[label]["task"]["scheduling_mode"] for label in GRAFTED_TASKS}
    assert modes == {
        DIAGNOSTIC: "manual",
        REWORK: "automatic",
        REWIRING: "automatic",
        TESTS: "automatic",
    }
    assert own[DIAGNOSTIC]["task"]["scheduling_mode"] == "automatic"
    links = {
        label: [each["predecessor_node_id"] for each in held[label]["predecessors"]]
        for label in (REWIRING, TESTS)
    }
    assert links == {
        REWIRING: [held[DIAGNOSTIC]["node_id"]],
        TESTS: [held[REWIRING]["node_id"]],
    }
    assert (study["task"]["start"], study["task"]["finish"]) == (
        own[DIAGNOSTIC]["task"]["start"],
        own[TESTS]["task"]["finish"],
    )


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_lines_grafted_are_budgeted_at_nought_and_the_provision_is_removed(
    ready: Occurring,
) -> None:
    # The lines keep their figures and their re-estimated amount, at a budgeted amount of nought,
    # as the own estimate holds them: a line it adds is no line of the reference (EP-30, whose own
    # estimate reads the reference by the lineages of the main structure); the provision line has
    # gone;
    # the total of ``Étude``, 600 and the provision of 60, moves to 600 and the 200 grafted: by 200
    # less the provision. ``Réalisation`` keeps its total; its float grows with the project.
    own = _by_label(ready.own())
    before = _by_label(ready.main())
    provision = ready.read()["provision_node_id"]
    _grafted(ready, _asked(ready))
    after = _by_label(ready.main())
    for label, amount in GRAFTED_LINES.items():
        line = after[label]["estimate_line"]
        assert (line["budgeted_amount"], line["reestimated_amount"]) == ("0.00", amount)
        assert own[label]["estimate_line"]["budgeted_amount"] == "0.00"
        assert line["quantity"] == own[label]["estimate_line"]["quantity"]
    assert provision not in {each["node_id"] for each in after.values()}
    study_before = Decimal(before[STUDY]["task"]["reestimated_amount"])
    study_after = Decimal(after[STUDY]["task"]["reestimated_amount"])
    assert (study_before, study_after) == (Decimal("660.00"), Decimal("800.00"))
    assert study_after - study_before == Decimal(200) - Decimal(60)
    assert (
        after[MAKING]["task"]["reestimated_amount"] == before[MAKING]["task"]["reestimated_amount"]
    )


@pytest.mark.requirement("WF-RIS-0060-A")
def test_after_a_milestone_the_tasks_follow_it_and_it_stays_a_milestone(
    ready: Occurring,
) -> None:
    # The provision moved to the milestone ``Recette``, at the first level before ``Clôture``: the
    # tasks of the own estimate come right after it, in their order, ``Clôture`` after them; the
    # milestone bears no subtask, of nought duration, and is named by no difference.
    path = f"{ready.main_path()}/nodes"
    headers = ready.risks.headers
    for label, days in (("Recette", "0"), ("Clôture", "1")):
        task = {"label": label, "duration": {"value": days, "unit": "d"}}
        sent = {"kind": "task", "parent_id": None, "task": task}
        answer = ready.api.post(path, headers=headers, json=sent)
        assert answer.status_code == 201, answer.text
    milestone = _by_label(ready.main())["Recette"]
    ready.risks.provisioned(ready.read(), provision_task_id=milestone["node_id"])
    asked = _asked(ready)
    assert str(asked.bearer_id) == milestone["node_id"]
    report = _grafted(ready, asked, applied=False)
    assert "updated" not in [each["change"] for each in report.differences]
    _grafted(ready, asked)
    main = ready.main()
    assert _children(main, None) == [STUDY, MAKING, "Recette", DIAGNOSTIC, REWORK, "Clôture"]
    held = _by_label(main)["Recette"]
    assert _children(main, held["node_id"]) == []
    assert (held["task"]["is_milestone"], held["task"]["duration"]["value"]) == (True, "0")


def test_each_node_grafted_comes_from_the_risk_and_the_rest_from_none(ready: Occurring) -> None:
    # ``origin_risk_id`` on every task and line grafted (WF-RIS-0060); none elsewhere.
    asked = _asked(ready)
    _grafted(ready, asked)
    held = _by_label(ready.main())
    grafted = {*GRAFTED_TASKS, *GRAFTED_LINES}
    assert {label for label, node in held.items() if node["origin_risk_id"]} == grafted
    assert {held[label]["origin_risk_id"] for label in grafted} == {str(asked.origin_risk_id)}


def test_the_graft_writes_what_its_report_said_and_leaves_the_own_estimate(
    ready: Occurring,
) -> None:
    # The report, computed alone, writes nothing; applied, the same differences are written, the
    # counter of the main structure advanced; the own estimate is as it was.
    asked = _asked(ready)
    own = ready.own()
    counter = ready.main_structure()["lock_version"]
    report = _grafted(ready, asked, applied=False)
    assert ready.main_structure()["lock_version"] == counter
    applied = _grafted(ready, asked)
    assert (applied.differences, applied.refusals) == (report.differences, ())
    assert ready.main_structure()["lock_version"] > counter
    assert ready.own() == own
    held = _by_label(ready.main())
    assert {str(each) for each in applied.copies.values()} == {
        held[label]["node_id"] for label in (*GRAFTED_TASKS, *GRAFTED_LINES)
    }


def test_a_graft_refused_by_its_report_writes_nothing(ready: Occurring) -> None:
    # The diagnostic left without an hour: the graft is refused by that reason, its parameters
    # those of the report, and the main structure is untouched.
    asked = _asked(ready)
    idle_diagnostic(ready)
    before = ready.main()
    report = _grafted(ready, asked, applied=False)
    with pytest.raises(UnprocessableError) as refused:
        _grafted(ready, asked)
    assert refused.value.code == "TASK_WITHOUT_WORKING_HOURS"
    assert refused.value.params == report.refusals[0]["params"]
    assert ready.main() == before


def test_a_risk_occurred_reads_the_reestimated_amount_of_its_lines_grafted(
    ready: Occurring,
) -> None:
    # The risk occurred and its own estimate grafted, ``getRisk`` reads it (#3981): its cost at
    # occurrence, and the re-estimated amount of the lines grafted, 120 and 80.
    _grafted(ready, _asked(ready))
    risk = ready.read()
    assert risk["state"] == "occurred"
    assert (risk["occurrence_cost"], risk["occurred_reestimated_amount"]) == ("200.00", "200.00")
    assert risk["provision_node_id"] is None


@pytest.mark.requirement("WF-RIS-0060-A")
def test_after_a_milestone_under_a_parent_the_tasks_take_its_parent_and_the_siblings_move_down(
    ready: Occurring,
) -> None:
    # ``Lot`` holds the milestone ``Jalon`` then ``Suite``: the tasks of the own estimate become
    # children of ``Lot``, right after the milestone, ``Suite`` last — its rank moved down by their
    # number; the milestone stays one and bears nothing.
    lot = main_task(ready, "Lot", None, "1")
    milestone = main_task(ready, "Jalon", lot["node_id"], "0")
    main_task(ready, "Suite", lot["node_id"], "1")
    ready.risks.provisioned(ready.read(), provision_task_id=milestone["node_id"])
    asked = _asked(ready)
    assert str(asked.bearer_id) == milestone["node_id"]
    _grafted(ready, asked)
    main = ready.main()
    held = _by_label(main)
    assert _children(main, lot["node_id"]) == ["Jalon", DIAGNOSTIC, REWORK, "Suite"]
    assert held[DIAGNOSTIC]["parent_id"] == held[REWORK]["parent_id"] == lot["node_id"]
    assert held["Suite"]["parent_id"] == lot["node_id"]
    assert _children(main, milestone["node_id"]) == []
    assert held["Jalon"]["task"]["is_milestone"] is True


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_total_of_the_summary_above_the_bearer_moves_by_the_lines_less_the_provision(
    ready: Occurring,
) -> None:
    # The provision borne by ``Sous-lot``, under the summary ``Lot``: the total of ``Lot`` moves by
    # the 200 of the lines grafted less the provision of 60, as the bearer's own does.
    lot = main_task(ready, "Lot", None, "1")
    bearer = main_task(ready, "Sous-lot", lot["node_id"], "1")
    ready.risks.provisioned(ready.read(), provision_task_id=bearer["node_id"])
    before = _by_label(ready.main())
    _grafted(ready, _asked(ready))
    after = _by_label(ready.main())
    for label in ("Lot", "Sous-lot"):
        moved = Decimal(after[label]["task"]["reestimated_amount"]) - Decimal(
            before[label]["task"]["reestimated_amount"]
        )
        assert moved == Decimal(200) - Decimal(60)
    assert after["Lot"]["task"]["is_summary"] is True
    assert after[STUDY]["task"]["reestimated_amount"] == "600.00", (
        "the provision left the study: nothing else moved there"
    )


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_tasks_grafted_are_not_started_whatever_the_own_estimate_held(
    ready: Occurring,
) -> None:
    # The own estimate is a plan: its tasks are not started; the graft writes them not started, with
    # neither start nor completion date, whatever its source's columns hold.
    _grafted(ready, _asked(ready))
    held = _by_label(ready.main())
    for label in GRAFTED_TASKS:
        task = held[label]["task"]
        assert (task["progress"], task["started_on"], task["completed_on"]) == (
            "not_started",
            None,
            None,
        )
