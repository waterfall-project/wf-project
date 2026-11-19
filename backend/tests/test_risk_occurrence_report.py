# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report of the occurrence of a risk, through the service (``getRiskOccurrenceReport``).

US-2620/L1. A read that writes nothing: the tasks and the lines of the own estimate added in the
order of its plan, the task bearing the provision changed by its dates and its duration, the
provision line removed and its amount, the reasons that refuse it (``TASK_WITHOUT_WORKING_HOURS``),
the counters read of the main structure and of the risk, and ``creates_current_revision``; a risk
that is not identified refused by 409, ``risk_identified`` missing (WF-RIS-0060). Every answer is
checked against the contract (``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import mark, refusal
from occurrence_support import (
    DIAGNOSTIC,
    OWN_PLAN,
    TESTS,
    Occurring,
    beyond_horizon,
    idle_diagnostic,
    occurring,
)
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, Risks, costed
from sqlalchemy import update

from waterfall.core.risks.tables import RiskEvaluation
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import submit

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

CONDITION = "STATE_FORBIDS_OPERATION"
# The provision of the risk: 200 at 30 %.
PROVISION = "60.00"


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
    """Give the risk identified in the second revision, its own estimate filled."""
    return occurring(api, project)


def _provision(ready: Occurring) -> dict[str, Any]:
    """Give the provision line of the risk in the main structure of the current revision."""
    line = ready.read()["provision_node_id"]
    return next(each for each in ready.main() if each["node_id"] == line)


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_report_adds_the_own_estimate_changes_its_bearer_and_removes_the_provision(
    ready: Occurring,
) -> None:
    # The tasks and the lines of the own estimate added in the order of its plan, without lineage;
    # ``Étude``, a leaf become the summary of the tasks grafted, which start a week after it,
    # changed by its duration and its dates; the provision line removed, its lineage named; no
    # refusal.
    provision = _provision(ready)
    study = next(each for each in ready.main() if each["kind"] == "task")
    assert study["task"]["label"] == STUDY
    report = ready.reported()
    added = [
        (each["change"], each["target"], each["lineage_id"], each["label"], each["fields"])
        for each in report["differences"][: len(OWN_PLAN)]
    ]
    assert added == [("added", kind, None, label, []) for kind, label in OWN_PLAN]
    assert report["differences"][len(OWN_PLAN) :] == [
        {
            "change": "updated",
            "target": "task",
            "lineage_id": study["lineage_id"],
            "label": STUDY,
            "predecessor_label": None,
            "fields": ["duration", "start", "finish"],
        },
        {
            "change": "removed",
            "target": "estimate_line",
            "lineage_id": provision["lineage_id"],
            "label": provision["estimate_line"]["label"],
            "predecessor_label": None,
            "fields": [],
        },
    ]
    assert (report["provision_amount"], report["refusals"]) == (PROVISION, [])


def test_the_report_returns_the_counters_read_and_writes_nothing(ready: Occurring) -> None:
    # The counter of the main structure and of the risk as read; the current revision exists. The
    # report read twice gives the same, the structures and the risk untouched.
    before = (ready.main(), ready.own(), ready.read(), ready.main_structure())
    report = ready.reported()
    assert report["main_structure_lock_version"] == before[3]["lock_version"]
    assert report["risk_lock_version"] == before[2]["lock_version"]
    assert report["creates_current_revision"] is False
    assert ready.reported() == report
    after = (ready.main(), ready.own(), ready.read(), ready.main_structure())
    assert after == before


def test_without_a_current_revision_the_report_is_judged_on_the_last_marked_one(
    ready: Occurring,
) -> None:
    # The second revision marked, the report is that of the occurrence which would open the next,
    # its counter that of the main structure the marking froze.
    mark(ready.project.stage, ready.revision, "v2.0")
    report = ready.reported()
    assert report["creates_current_revision"] is True
    held = ready.main_structure(ready.revision["revision_id"])
    assert report["main_structure_lock_version"] == held["lock_version"]
    assert [each["label"] for each in report["differences"][:1]] == [DIAGNOSTIC]
    assert report["provision_amount"] == PROVISION


@pytest.mark.parametrize("state", ["occurred", "dismissed"])
def test_a_risk_that_is_not_identified_is_refused(ready: Occurring, state: str) -> None:
    # Only an identified risk occurs (WF-RIS-0020): 409, ``risk_identified`` missing.
    with ready.project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(
                RiskEvaluation.risk_id == UUID(ready.risk["risk_id"]),
                RiskEvaluation.revision_id == UUID(ready.revision["revision_id"]),
            )
            .values(
                state=state,
                provision_node_id=None,
                occurrence_cost=Decimal(200) if state == "occurred" else None,
            )
        )
    answer = ready.report()
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "risk_identified"})


def test_a_project_without_a_reference_is_refused_before_the_risk(
    api: ContractClient, project: Costed
) -> None:
    # The conditions of the project come first: no reference, ``reference_revision_designated``;
    # an unknown risk of a project without one is refused the same way.
    risks = Risks(api, project)
    risk = risks.declared_costed()
    path = f"{risks.base}/risks/{risk['risk_id']}/occurrence"
    answer = api.get(path, headers=risks.headers)
    assert refusal(answer) == (
        409,
        CONDITION,
        {"missing_condition": "reference_revision_designated"},
    )


def test_an_unknown_risk_is_not_found(ready: Occurring) -> None:
    path = f"{ready.risks.base}/risks/{ready.project.tasks[STUDY]}/occurrence"
    answer = ready.api.get(path, headers=ready.risks.headers)
    assert answer.status_code == 404


def test_a_task_its_roles_leave_without_hours_refuses_the_occurrence(ready: Occurring) -> None:
    # The diagnostic bears two labour lines, a welder and a fitter both on weekdays; the fitter's
    # calendar then moved to the weekend around the service, as a change of the reference after the
    # revision was opened: the diagnostic would be left without an hour, and the report names the
    # roles and the task, as the own estimate holds it (WF-PLA-0010).
    welder, fitter, diagnostic = idle_diagnostic(ready)
    report = ready.reported()
    assert [each["code"] for each in report["refusals"]] == ["TASK_WITHOUT_WORKING_HOURS"]
    params = report["refusals"][0]["params"]
    assert {each["resource_role_id"] for each in params["resource_roles"]} == {
        str(welder),
        str(fitter),
    }
    assert params["tasks"] == [
        {
            "project_id": str(ready.project.project_id),
            "node_id": str(diagnostic),
            "label": DIAGNOSTIC,
        }
    ]
    # The dates are not computed: the task bearing the provision is named by no difference.
    assert [each["change"] for each in report["differences"]][-1:] == ["removed"]
    assert "updated" not in [each["change"] for each in report["differences"]]


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_provision_removed_is_the_amount_of_its_line_not_a_recomputation(
    ready: Occurring,
) -> None:
    # A probability that is not round, 0.333, written on the evaluation around the service: the
    # severity weighted would give 66.60, but the line still holds 60.00, and the report gives the
    # amount of the line, "the amount of the line removed" (``RiskOccurrenceReport``).
    with ready.project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(
                RiskEvaluation.risk_id == UUID(ready.risk["risk_id"]),
                RiskEvaluation.revision_id == UUID(ready.revision["revision_id"]),
            )
            .values(probability=Decimal("0.333"))
        )
    line = _provision(ready)["estimate_line"]
    assert line["reestimated_amount"] == PROVISION
    assert ready.reported()["provision_amount"] == line["reestimated_amount"]


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_task_grafted_beyond_the_horizon_refuses_the_occurrence_by_its_own_estimate_node(
    ready: Occurring,
) -> None:
    # The diagnostic of the own estimate pushed to 2060, its successors with it: the engine finds
    # the last to finish beyond the horizon, ``PROJECT_HORIZON_EXCEEDED``, named by its node of the
    # own estimate and its label, as ``TASK_WITHOUT_WORKING_HOURS`` names its tasks (``ProblemTask``
    # has no null node; #4151).
    beyond_horizon(ready, DIAGNOSTIC)
    last = next(
        each for each in ready.own() if each["kind"] == "task" and each["task"]["label"] == TESTS
    )
    report = ready.reported()
    assert [each["code"] for each in report["refusals"]] == ["PROJECT_HORIZON_EXCEEDED"]
    assert report["refusals"][0]["params"] == {"task": {"node_id": last["node_id"], "label": TESTS}}


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_terminal_project_is_refused_before_the_risk(ready: Occurring) -> None:
    put_in_state(ready.project.stage.owner, ready.project.stage.project["project_id"], "completed")
    answer = ready.report()
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "project_not_terminal"})


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_background_task_writing_in_the_project_refuses_the_report(
    ready: Occurring, queue: TaskQueue
) -> None:
    # A marking queued around the service: the report waits for it, as the occurrence does.
    stage = ready.project.stage
    payload = {"project_id": stage.project["project_id"]}
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    answer = ready.report()
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "no_background_task_running"})


@pytest.mark.requirement("WF-RIS-0060-A")
def test_without_a_current_revision_a_reader_who_may_not_create_one_is_refused(
    ready: Occurring, realm: TestRealm
) -> None:
    # The occurrence would create the revision (WF-RIS-0060): who lacks ``revisions.write`` has
    # ``may_create_revision`` missing, after the conditions of the project and of the risk.
    stage = ready.project.stage
    mark(stage, ready.revision, "v2.0")
    reader = person(stage.database, realm, "risks.read", "planning.read", "estimate.read")
    contribute(stage.database, stage.project["project_id"], reader, "contributor")
    answer = ready.api.get(
        f"{PROJECTS}/{ready.project.project_id}/risks/{ready.risk['risk_id']}/occurrence",
        headers=reader.headers,
    )
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "may_create_revision"})
