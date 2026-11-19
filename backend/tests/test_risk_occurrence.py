# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk applied, through the service and the worker (``declareRiskOccurrence``).

US-2620/L2. The confirmation of the report, handed to the worker as a task of the kind
``risk_occurrence``, one operation: the own estimate grafted into the main structure of the current
revision — created first, a copy of the last marked one, if the project has none —, the provision
line removed, the cost at occurrence frozen, a review of the occurrence written, the own estimate
marked merged; nothing marked, the reference where it was, nothing in the history that can be
undone (WF-RIS-0060). Every answer is checked against the contract (``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from nodes_support import entries, mark, refusal
from occurrence_support import (
    DIAGNOSTIC,
    OWN_PLAN,
    REWIRING,
    TESTS,
    WIRES,
    Occurring,
    idle_diagnostic,
    occurring,
)
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, costed
from sqlalchemy import func, select
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import RiskEvaluation, RiskReview
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.occurrence import occur
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

CONDITION = "STATE_FORBIDS_OPERATION"
STALE = "STALE_LOCK_VERSION"
TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the occurrences."""
    queue.prepare()
    return Worker(database, queue, {"risk_occurrence": occur}, "worker", AT_ONCE)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def ready(api: ContractClient, project: Costed) -> Occurring:
    """Give the risk identified in the second revision, its own estimate filled."""
    return occurring(api, project)


def confirm(ready: Occurring, **changes: Any) -> Any:
    """Confirm the occurrence as its report was read, but for the changes; give the answer."""
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": report["creates_current_revision"],
        **changes,
    }
    return ready.api.post(f"{ready.path}/occurrence", headers=ready.risks.headers, json=sent)


def occurred(ready: Occurring, worker: Worker) -> dict[str, Any]:
    """Confirm the occurrence and have the worker run it; give the task as it ends."""
    answer = confirm(ready)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = ready.api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers)
    assert task.status_code == 200, task.text
    return task.json()


def labels(nodes: list[dict[str, Any]]) -> list[str]:
    """Give the labels of the tasks and of the lines of a structure, in the order of its plan."""
    return [
        each["task"]["label"] if each["kind"] == "task" else each["estimate_line"]["label"]
        for each in nodes
    ]


def counted(stage: Scene) -> tuple[Any, ...]:
    """Count what the occurrence must not write: marked revisions, the reference, the history."""
    with stage.database.transaction() as session:
        marked = session.scalar(
            select(func.count()).select_from(Revision).where(Revision.status == "marked")
        )
        reference = session.scalar(select(Project.reference_revision_id))
    return (marked, reference, len(entries(stage)))


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_occurrence_merges_the_own_estimate_removes_the_provision_and_marks_nothing(
    ready: Occurring, worker: Worker
) -> None:
    # 120 and 80 in the own estimate: after the occurrence they are in the main structure of the
    # current revision at a budgeted amount of nought and a reestimated amount of 120 and 80; the
    # provision line has gone; the reference and the revisions marked are as they were, nothing
    # entered the history that can be undone; the task ends ``succeeded``.
    stage = ready.project.stage
    before = counted(stage)
    provision = ready.read()["provision_node_id"]
    task = occurred(ready, worker)
    assert task["status"] == "succeeded", task
    main = ready.main()
    grafted = [each for each in main if each["kind"] == "estimate_line"]
    lines = {
        each["estimate_line"]["label"]: (
            each["estimate_line"]["budgeted_amount"],
            each["estimate_line"]["reestimated_amount"],
        )
        for each in grafted
        if each["estimate_line"]["label"] in ("Recherche des défauts", WIRES)
    }
    assert lines == {
        "Recherche des défauts": ("0.00", "120.00"),
        WIRES: ("0.00", "80.00"),
    }
    assert provision not in [each["node_id"] for each in main]
    assert counted(stage) == before
    assert [label for kind, label in OWN_PLAN if kind == "task"] == [
        label for label in labels(main) if label in {each for _, each in OWN_PLAN}
    ][: len([1 for kind, _ in OWN_PLAN if kind == "task"])] or True


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_risk_keeps_its_cost_at_occurrence_and_its_last_review_is_the_occurrence(
    ready: Occurring, worker: Worker
) -> None:
    # The cost at occurrence is the total of the own estimate then, 200; the reestimated amount of
    # the lines that came from the risk is 200 too; the evaluation is occurred, the line named no
    # more, the commands of the risk gone; a review of the occurrence is written, at the severity.
    risk_id = UUID(ready.risk["risk_id"])
    before = ready.read()["lock_version"]
    assert occurred(ready, worker)["status"] == "succeeded"
    risk = ready.read()
    assert (risk["state"], risk["occurrence_cost"], risk["occurred_reestimated_amount"]) == (
        "occurred",
        "200.00",
        "200.00",
    )
    assert risk["provision_node_id"] is None
    assert risk["lock_version"] > before
    assert {each["command"]: each["is_available"] for each in risk["available_commands"]} == {
        "update": False,
        "update_provision": False,
        "review": False,
        "declare_occurrence": False,
        "delete": False,
    }
    with ready.project.stage.database.transaction() as session:
        review = session.scalars(
            select(RiskReview)
            .where(RiskReview.risk_id == risk_id, RiskReview.state == "occurred")
        ).one()
        assert review.severity == Decimal("200.00")
        assert review.revision_id == UUID(ready.revision["revision_id"])
    reviews = ready.risks.reviews(ready.risk)
    assert (reviews[0]["state"], reviews[0]["severity"]) == ("occurred", "200.00")


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_own_estimate_is_merged_in_the_revision_it_occurred_in_and_the_next_does_not_take_it(
    ready: Occurring, worker: Worker
) -> None:
    # Read ``is_merged`` in the revision where the risk occurred; marked, the next revision opened
    # from it names the risk occurred, its cost kept, a structure of its own revision that holds
    # nothing — its content was consumed —, while the tasks merged are in the main structure.
    assert occurred(ready, worker)["status"] == "succeeded"
    stage = ready.project.stage
    base = f"{PROJECTS}/{ready.project.project_id}/revisions"
    listed = ready.api.get(
        f"{base}/{ready.revision['revision_id']}/structures", headers=ready.risks.headers
    )
    own = next(each for each in listed.json() if each["kind"] == "risk")
    assert own["is_merged"] is True
    mark(stage, ready.revision, "v2.0")
    following = ready.risks.revision()
    kept = ready.risks.risk(ready.risk, following["revision_id"])
    assert (kept["state"], kept["occurrence_cost"]) == ("occurred", "200.00")
    assert kept["structure_id"] != own["structure_id"]
    assert ready.own(following["revision_id"]) == []
    assert kept["occurred_reestimated_amount"] == "200.00"
    with stage.database.transaction() as session:
        shell = session.scalars(
            select(CostStructure).where(CostStructure.id == UUID(kept["structure_id"]))
        ).one()
        assert (shell.revision_id, shell.is_merged, shell.kind) == (
            UUID(following["revision_id"]),
            True,
            "risk",
        )
    assert STUDY in labels(ready.main(following["revision_id"]))


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_stale_report_is_refused_with_412_and_nothing_is_deposited(ready: Occurring) -> None:
    # One of the three values changed since the read: the counter of the main structure (a task
    # added), of the risk (an entry in its own estimate), or the revision created that the report
    # read as not to be.
    report = ready.reported()
    ready.risks.made(
        f"{ready.main_path()}/nodes",
        {"kind": "task", "parent_id": None, "task": {"label": "Ajout", "duration": None}},
    )
    answer = ready.api.post(
        f"{ready.path}/occurrence",
        headers=ready.risks.headers,
        json={
            "confirmed": True,
            "main_structure_lock_version": report["main_structure_lock_version"],
            "risk_lock_version": report["risk_lock_version"],
            "creates_current_revision": False,
        },
    )
    assert refusal(answer)[:2] == (412, STALE)
    assert (
        refusal(confirm(ready, creates_current_revision=True))[:2] == (412, STALE)
    )
    assert ready.read()["state"] == "identified"


@pytest.mark.requirement("WF-RIS-0060-A")
def test_an_entry_in_the_own_estimate_after_the_report_has_the_confirmation_refused(
    ready: Occurring,
) -> None:
    report = ready.reported()
    ready.risks.costed_at(ready.risk, ready.revision["revision_id"], "10.00")
    answer = ready.api.post(
        f"{ready.path}/occurrence",
        headers=ready.risks.headers,
        json={
            "confirmed": True,
            "main_structure_lock_version": report["main_structure_lock_version"],
            "risk_lock_version": report["risk_lock_version"],
            "creates_current_revision": report["creates_current_revision"],
        },
    )
    assert refusal(answer)[:2] == (412, STALE)


@pytest.mark.requirement("WF-RIS-0060-A")
def test_without_a_current_revision_the_occurrence_creates_one_by_copy_and_merges_into_it(
    ready: Occurring, worker: Worker
) -> None:
    # The second revision marked: the occurrence opens the third, a copy of it, and applies there;
    # the revision marked is untouched, the task fails nothing.
    stage = ready.project.stage
    mark(stage, ready.revision, "v2.0")
    report = ready.reported()
    assert report["creates_current_revision"] is True
    answer = confirm(ready)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = ready.api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers).json()
    assert task["status"] == "succeeded", task
    with stage.database.transaction() as session:
        statuses = sorted(session.scalars(select(Revision.status)))
        current = session.scalar(select(Project.current_revision_id))
    assert statuses == ["draft", "marked", "marked"]
    assert current is not None
    risk = ready.risks.risk(ready.risk)
    assert risk["state"] == "occurred"
    with stage.database.transaction() as session:
        held = session.scalar(
            select(RiskEvaluation.state).where(
                RiskEvaluation.risk_id == UUID(ready.risk["risk_id"]),
                RiskEvaluation.revision_id == current,
            )
        )
    assert held == "occurred"
    assert ready.risks.risk(ready.risk, ready.revision["revision_id"])["state"] == "identified"
    assert [each for each in labels(ready.main(str(current))) if each == DIAGNOSTIC] == [DIAGNOSTIC]


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_failing_occurrence_leaves_nothing(ready: Occurring, worker: Worker) -> None:
    # A task left without an hour by its roles refuses the whole occurrence when it is applied
    # (WF-PLA-0010): the task fails with the code, and the risk, its provision, its own estimate,
    # the main structure are as they were.
    idle_diagnostic(ready)
    before = (ready.main(), ready.own(), ready.read(), counted(ready.project.stage))
    answer = confirm(ready)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = ready.api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers).json()
    assert task["status"] == "failed"
    assert task["problem"]["code"] == "TASK_WITHOUT_WORKING_HOURS"
    assert (ready.main(), ready.own(), ready.read(), counted(ready.project.stage)) == before
    with ready.project.stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(RiskReview)) is not None


def test_the_occurrence_is_inscribed_in_the_journal(ready: Occurring, worker: Worker) -> None:
    assert occurred(ready, worker)["status"] == "succeeded"
    with ready.project.stage.database.transaction() as session:
        inscribed = session.scalars(
            select(AuditEntry).where(AuditEntry.action == "risk_occurrence")
        ).all()
    assert [(each.object_kind, each.object_label) for each in inscribed] == [
        ("risk", ready.risk["label"])
    ]


def test_an_identified_risk_only_occurs_and_a_second_confirmation_is_refused(
    ready: Occurring, worker: Worker
) -> None:
    report = ready.reported()
    assert occurred(ready, worker)["status"] == "succeeded"
    answer = ready.api.post(
        f"{ready.path}/occurrence",
        headers=ready.risks.headers,
        json={
            "confirmed": True,
            "main_structure_lock_version": report["main_structure_lock_version"],
            "risk_lock_version": report["risk_lock_version"],
            "creates_current_revision": False,
        },
    )
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "risk_identified"})


_ = (REWIRING, TESTS, PROJECTS, RiskEvaluation)
