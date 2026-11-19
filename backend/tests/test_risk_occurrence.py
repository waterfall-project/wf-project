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
from uuid import UUID, uuid4

import pytest
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from nodes_support import entries, mark, refusal
from occurrence_support import (
    DIAGNOSTIC,
    OWN_PLAN,
    REWORK,
    SEARCH,
    WIRES,
    Occurring,
    fill_own_estimate,
    idle_diagnostic,
    occurring,
)
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, costed, material
from sqlalchemy import func, select
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import RiskEvaluation, RiskReview
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import submit
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
    # The tasks of the first level of the own estimate are the last under the task that bore the
    # provision, in their order, the whole plan following it.
    study = next(each for each in main if each["kind"] == "task" and labels([each]) == [STUDY])
    top = [each for each in main if labels([each])[0] in (DIAGNOSTIC, REWORK)]
    assert [(each["parent_id"], labels([each])[0]) for each in top] == [
        (study["node_id"], DIAGNOSTIC),
        (study["node_id"], REWORK),
    ]
    plan = [label for _, label in OWN_PLAN]
    held = labels(main)
    assert held[held.index(DIAGNOSTIC) :][: len(plan)] == plan


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
            select(RiskReview).where(RiskReview.risk_id == risk_id, RiskReview.state == "occurred")
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
    assert refusal(confirm(ready, creates_current_revision=True))[:2] == (412, STALE)
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
        written = session.scalars(select(RiskReview.state).where(RiskReview.state == "occurred"))
        assert list(written) == []


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


def origins(nodes: list[dict[str, Any]]) -> dict[str, str | None]:
    """Give the risk each task and each line of a structure comes from, by label."""
    return {label: each["origin_risk_id"] for label, each in zip(labels(nodes), nodes, strict=True)}


MERGED = (*(label for _, label in OWN_PLAN),)


@pytest.mark.requirement("WF-RIS-0060-A")
def test_each_task_and_line_merged_names_the_risk_and_a_creation_under_them_names_none(
    ready: Occurring, worker: Worker
) -> None:
    # #1762: the occurrence marks every task and every line it merges with its risk; a task or a
    # line created afterwards, even under a task issued from the risk, comes from none.
    assert occurred(ready, worker)["status"] == "succeeded"
    risk_id = ready.risk["risk_id"]
    held = origins(ready.main())
    assert {label: held[label] for label in MERGED} == dict.fromkeys(MERGED, risk_id)
    assert held[STUDY] is None
    rework = next(each for each in ready.main() if labels([each]) == [REWORK])
    task = ready.risks.made(
        f"{ready.main_path()}/nodes",
        {"kind": "task", "parent_id": rework["node_id"], "task": {"label": "Ajoutée"}},
    )
    line = ready.risks.made(
        f"{ready.main_path()}/nodes",
        {
            "kind": "estimate_line",
            "parent_id": task["node_id"],
            "estimate_line": material(ready.project.costs, "Ajoutée", "5.00"),
        },
    )
    assert (task["origin_risk_id"], line["origin_risk_id"]) == (None, None)


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_trace_of_the_risk_stays_in_the_next_revision_and_after_a_move(
    ready: Occurring, worker: Worker
) -> None:
    # The copy of a revision and the move of a task under another keep what the occurrence wrote.
    assert occurred(ready, worker)["status"] == "succeeded"
    risk_id = ready.risk["risk_id"]
    rework = next(each for each in ready.main() if labels([each]) == [REWORK])
    moved = ready.api.post(
        f"{ready.main_path()}/nodes/move",
        headers=ready.risks.headers,
        json={
            "node_ids": [rework["node_id"]],
            "parent_id": None,
            "lock_version": ready.main_structure()["lock_version"],
        },
    )
    assert moved.status_code == 200, moved.text
    held = origins(ready.main())
    assert {label: held[label] for label in MERGED} == dict.fromkeys(MERGED, risk_id)
    mark(ready.project.stage, ready.revision, "v2.0")
    following = ready.risks.revision()
    copied = origins(ready.main(following["revision_id"]))
    assert {label: copied[label] for label in MERGED} == dict.fromkeys(MERGED, risk_id)


def _asked(ready: Occurring, query: str, base: str | None = None) -> Any:
    """Read the main structure of the current revision, as the query filters it."""
    return ready.api.get(f"{base or ready.main_path()}/nodes{query}", headers=ready.risks.headers)


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_grids_filter_on_the_tasks_and_lines_issued_from_a_risk_or_from_a_given_one(
    ready: Occurring, worker: Worker
) -> None:
    # ``is_from_risk`` and ``origin_risk_ids`` retain the nodes the occurrence merged — with their
    # ancestors, as any filter does —, in ``listNodes`` and in ``compareRevisions``; the risk
    # asked, the node of another risk is left out; an identifier that is no occurred risk of the
    # project is refused with 422, ``UNKNOWN_RISK`` on its place in the list.
    assert occurred(ready, worker)["status"] == "succeeded"
    risk_id = ready.risk["risk_id"]
    merged = {label for _, label in OWN_PLAN}
    every = labels(ready.main())
    for query in ("?is_from_risk=true", f"?origin_risk_ids={risk_id}"):
        found = _asked(ready, query)
        assert found.status_code == 200, found.text
        kept = set(labels(found.json()["items"]))
        assert merged <= kept <= merged | {STUDY}
    others = _asked(ready, "?is_from_risk=false").json()["items"]
    assert not merged & set(labels(others))
    assert STUDY in labels(others)
    assert set(every) >= merged
    unknown = uuid4()
    for query in (f"?origin_risk_ids={unknown}", f"?origin_risk_ids={risk_id},{unknown}"):
        answer = _asked(ready, query)
        place = query.count(",")
        assert answer.status_code == 422, answer.text
        assert answer.json()["fields"] == [
            {"pointer": f"/query/origin_risk_ids/{place}", "code": "UNKNOWN_RISK"}
        ]
    base = f"{PROJECTS}/{ready.project.project_id}/revisions/comparison"
    revisions = (
        f"from_revision_id={ready.first['revision_id']}"
        f"&to_revision_id={ready.revision['revision_id']}"
    )
    compared = ready.api.get(
        f"{base}?{revisions}&is_from_risk=true&fields=kind,task.label,estimate_line.label",
        headers=ready.risks.headers,
    )
    assert compared.status_code == 200, compared.text
    assert merged <= set(labels(compared.json()["items"]))
    refused = ready.api.get(
        f"{base}?{revisions}&origin_risk_ids={unknown}", headers=ready.risks.headers
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["fields"][0]["code"] == "UNKNOWN_RISK"


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_risk_still_identified_is_no_origin_the_filters_know(ready: Occurring) -> None:
    # Before its occurrence nothing comes from the risk: the filter refuses it as an unknown one.
    answer = _asked(ready, f"?origin_risk_ids={ready.risk['risk_id']}")
    assert answer.status_code == 422, answer.text
    assert answer.json()["fields"][0]["code"] == "UNKNOWN_RISK"


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_line_merged_and_reestimated_shows_beside_a_cost_at_occurrence_that_stays(
    ready: Occurring, worker: Worker
) -> None:
    # The cost at occurrence is frozen at 200; a line merged reestimated from 120 to 200 makes the
    # reestimated amount of the risk 280, beside a cost that does not move (WF-RIS-0060; #1761).
    # The coverage that sums them is US-2610's.
    assert occurred(ready, worker)["status"] == "succeeded"
    line = next(
        each
        for each in ready.main()
        if each["kind"] == "estimate_line" and each["estimate_line"]["label"] == SEARCH
    )
    answer = ready.api.patch(
        f"{ready.main_path()}/nodes/{line['node_id']}/estimate-line",
        headers=ready.risks.headers,
        json={"lock_version": line["lock_version"], "unit_disbursement": "200.00"},
    )
    assert answer.status_code == 200, answer.text
    risk = ready.read()
    assert (risk["occurrence_cost"], risk["occurred_reestimated_amount"]) == ("200.00", "280.00")


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_confirmation_is_refused_by_the_conditions_of_the_project_and_of_the_revision(
    ready: Occurring, queue: TaskQueue
) -> None:
    # In the order of the 409 the report names: a project writing in a task — here a marking queued
    # around the service —, then a terminal project, both before the risk is read; a risk unknown is not found.
    stage = ready.project.stage
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": False,
    }
    path = f"{ready.path}/occurrence"
    unknown = f"{ready.risks.base}/risks/{uuid4()}/occurrence"
    assert ready.api.post(unknown, headers=ready.risks.headers, json=sent).status_code == 404
    payload = {"project_id": stage.project["project_id"]}
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    answer = ready.api.post(path, headers=ready.risks.headers, json=sent)
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "no_background_task_running"})
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    answer = ready.api.post(path, headers=ready.risks.headers, json=sent)
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "project_not_terminal"})


@pytest.mark.requirement("WF-RIS-0060-A")
def test_who_may_not_create_the_revision_is_refused_and_who_lacks_the_permission_is_forbidden(
    ready: Occurring, realm: TestRealm
) -> None:
    # Without a current revision the occurrence creates one: ``may_create_revision`` is missing for
    # who lacks ``revisions.write`` (409); who lacks ``risk_occurrence`` is forbidden (403).
    stage = ready.project.stage
    mark(stage, ready.revision, "v2.0")
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": True,
    }
    path = f"{ready.path}/occurrence"
    keeper = person(stage.database, realm, "risks.read", "risk_occurrence", "planning.read")
    contribute(stage.database, stage.project["project_id"], keeper, "contributor")
    answer = ready.api.post(path, headers=keeper.headers, json=sent)
    assert refusal(answer) == (409, CONDITION, {"missing_condition": "may_create_revision"})
    reader = person(stage.database, realm, "risks.read")
    contribute(stage.database, stage.project["project_id"], reader, "contributor")
    assert ready.api.post(path, headers=reader.headers, json=sent).status_code == 403


@pytest.mark.requirement("WF-RIS-0060-A")
def test_only_abandoning_the_current_revision_undoes_an_occurrence(
    ready: Occurring, worker: Worker
) -> None:
    # No command undoes it: the revision abandoned, the risk is identified again, as the revision
    # marked held it — its provision line, no cost at occurrence — and its tasks are gone.
    assert occurred(ready, worker)["status"] == "succeeded"
    assert ready.read()["state"] == "occurred"
    ready.risks.abandon(ready.revision)
    risk = ready.risks.risk(ready.risk)
    assert (risk["state"], risk["occurrence_cost"]) == ("identified", None)
    assert risk["provision_node_id"] is not None


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_risk_declared_and_occurred_in_the_revision_abandoned_goes_with_it(
    ready: Occurring, worker: Worker
) -> None:
    # The risk exists in that revision alone: the tasks it merged name it (``origin_risk_id``), and
    # the abandonment deletes them with the risk, which their key would otherwise refuse.
    second = ready.risks.declared(label="Défaut de livraison")
    fill_own_estimate(ready.risks, second, ready.revision["revision_id"])
    held = Occurring(ready.api, ready.project, ready.risks, second, ready.first, ready.revision)
    assert occurred(held, worker)["status"] == "succeeded"
    ready.risks.abandon(ready.revision)
    assert ready.risks.read(second).status_code == 404
    with ready.project.stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(RiskEvaluation)) == 1
