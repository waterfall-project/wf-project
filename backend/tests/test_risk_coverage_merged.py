# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The coverage of the risks after an occurrence and after a merge, on the real ones (US-2610/L2).

The examples of the Vérif of WF-RIS-0050 that ask for the occurrence of a risk or the merge of a
differential, and the one of WF-RAE-0010 on an amendment, through the service and the worker: a
risk of severity 200 at 30 % in the reference (reserve 60) whose own estimate is reassessed to 250
before it occurs, then the figures of the coverage after the occurrence, after the completion of the
tasks that came from it, after the reestimation of their lines, after three amendments, and across
two references. Every answer is checked against the contract (``ContractClient``).

The merge asks an up to date differential (#4034): an amendment is opened after the occurrence, or
updated before it is merged when the main structure moved since its opening.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import OutOfDate, node_labelled, on, opened_amendment
from estimate_support import Costing, Lines, costing
from merges_support import client, lines_of, merged, tasks_of
from nodes_support import Tree, set_progress
from occurrence_support import SEARCH, WIRES, Occurring, occurring
from projects_support import PROJECTS
from projects_support import scene as make_scene
from rebases_support import rebased
from risks_support import MAKING, Costed, Risks, costed
from sqlalchemy import select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.risks.tables import RiskReferenceShare
from waterfall.platform.database import utc_now
from waterfall.worker.merge import merge
from waterfall.worker.occurrence import occur
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
# The figures of a coverage, in the order of the contract: the reserve, the provisions left, the
# cost of the occurred, their reestimated, the variance.
Figures = tuple[str, str, str, str, str]
# After the occurrence of the risk reassessed to 250: reserve 60, nothing left, 250 and 250 beside.
OCCURRED: Figures = ("60.00", "0.00", "250.00", "250.00", "-190.00")


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the occurrences and the merges."""
    queue.prepare()
    handlers = {"risk_occurrence": occur, "structure_merge": merge}
    return Worker(database, queue, handlers, "worker", AT_ONCE)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


def reassessed(api: ContractClient, project: Costed, *, second: bool = False) -> Occurring:
    """Give the risk identified in the second revision, its own estimate reassessed to 250.

    Declared at 200 and 30 % in the reference (60), with ``second`` a second risk of 400 at 10 %
    beside it (40), then its own estimate of 120 and 80 brought to 170 and 80 before it occurs.
    """
    if second:
        risks = Risks(api, project)
        other = risks.declared("0.1", "Panne de la grue")
        risks.costed_at(other, project.revision_id, "400.00")
    ready = occurring(api, project)
    line = next(
        each
        for each in ready.own()
        if each["kind"] == "estimate_line" and each["estimate_line"]["label"] == SEARCH
    )
    ready.risks.repriced(ready.risk, ready.revision["revision_id"], line, "170.00")
    return ready


def occurred(ready: Occurring, worker: Worker) -> None:
    """Confirm the occurrence of the risk and have the worker run it."""
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": report["creates_current_revision"],
    }
    answer = ready.api.post(f"{ready.path}/occurrence", headers=ready.risks.headers, json=sent)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = ready.api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers)
    assert task.json()["status"] == "succeeded", task.text


def in_current(ready: Occurring) -> Costed:
    """Give the project as it stands in the current revision, after the occurrence."""
    tree = Tree(ready.api, ready.project.stage, ready.revision)
    held = tasks_of(ready.project, tree.structure_id)
    tasks = {label: node for label, (node, _, _) in held.items()}
    return replace(
        ready.project,
        tree=tree,
        lines=Lines(tree),
        revision_id=UUID(ready.revision["revision_id"]),
        structure_id=UUID(tree.structure_id),
        tasks=tasks,
    )


def coverage(ready: Occurring, revision_id: object = None) -> Figures:
    """Read the coverage of the project in a revision, the current one by default."""
    query = "" if revision_id is None else f"?revision_id={revision_id}"
    path = f"{PROJECTS}/{ready.project.project_id}/risks/coverage{query}"
    answer = ready.api.get(path, headers=ready.risks.headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    return (
        body["reserve"],
        body["remaining_provisions"],
        body["occurred_cost"],
        body["occurred_reestimated"],
        body["coverage_variance"],
    )


def budget(ready: Occurring, revision_id: object = None) -> Decimal:
    """Read the budget of the reference in a revision: the budgets of its subprojects, summed."""
    query = "" if revision_id is None else f"?revision_id={revision_id}"
    path = f"{PROJECTS}/{ready.project.project_id}/remaining-indicators{query}"
    answer = ready.api.get(path, headers=ready.risks.headers)
    assert answer.status_code == 200, answer.text
    return sum((Decimal(each["budget"]) for each in answer.json()["by_subproject"]), Decimal(0))


def shares(ready: Occurring, revision_id: object) -> dict[UUID, Decimal]:
    """Give the shares a reference revision conserves, by risk."""
    with ready.project.stage.owner.begin() as connection:
        rows = connection.execute(
            select(RiskReferenceShare.risk_id, RiskReferenceShare.provision_amount).where(
                RiskReferenceShare.revision_id == revision_id
            )
        )
        return dict(rows.all())


def remaining(api: ContractClient, project: Costed, revision_id: object = None) -> Decimal:
    """Read the total of the remaining to commit of a revision, the current one by default."""
    query = "" if revision_id is None else f"?revision_id={revision_id}"
    path = f"{PROJECTS}/{project.project_id}/remaining-indicators{query}"
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return Decimal(answer.json()["total"])


def line_named(current: Costed, label: str) -> dict[str, Any]:
    """Read a line of the main structure of the current revision."""
    return node_labelled(current.tree, label)


# --- After the occurrence -----------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0050-A")
def test_after_the_occurrence_at_250_the_budget_stays_1000_and_the_variance_is_minus_190(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Après survenance de ce risque, réévalué à 250, le budget de référence vaut toujours 1 000,
    # les provisions restantes 0, le coût des survenus 250, et l'écart de couverture -190. »
    ready = reassessed(api, project)
    assert coverage(ready) == ("60.00", "75.00", "0.00", "0.00", "-15.00")
    occurred(ready, worker)
    assert budget(ready) == Decimal("1000.00")
    assert coverage(ready) == OCCURRED
    assert ready.read()["occurrence_cost"] == "250.00"


@pytest.mark.requirement("WF-RIS-0050-A")
def test_dismissing_a_second_risk_of_40_after_the_occurrence_takes_the_variance_to_minus_150(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Sur le même projet, un second risque de provision 40 présent dans la référence porte la
    # réserve à 100 ; l'écarter fait passer les provisions restantes de 40 à 0 sans toucher le
    # budget de référence, et l'écart de couverture de -190 à -150. » The first risk occurred at
    # 250.
    ready = reassessed(api, project, second=True)
    occurred(ready, worker)
    assert coverage(ready) == ("100.00", "40.00", "250.00", "250.00", "-190.00")
    other = next(
        each
        for each in ready.api.get(f"{ready.risks.base}/risks", headers=ready.risks.headers).json()[
            "items"
        ]
        if each["label"] == "Panne de la grue"
    )
    ready.risks.reviewed(other, state="dismissed")
    assert coverage(ready) == ("100.00", "0.00", "250.00", "250.00", "-150.00")
    assert budget(ready) == Decimal("1000.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_completion_of_the_tasks_of_the_occurred_risk_changes_neither_cost_nor_variance(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « La terminaison des tâches issues d'un risque survenu ne change ni le coût des survenus ni
    # l'écart de couverture. » The tasks the occurrence merged, completed one after the other.
    ready = reassessed(api, project)
    occurred(ready, worker)
    current = in_current(ready)
    before = coverage(ready)
    assert before == OCCURRED
    grafted = [
        node
        for label, (node, _, _) in tasks_of(project, current.structure_id).items()
        if label in ("Diagnostic des défauts", "Recâblage des armoires", "Essais")
    ]
    assert len(grafted) == 3
    for node in grafted:
        set_progress(project.stage, str(node), "completed", date(2026, 11, 13))
    assert coverage(ready) == before


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_reestimation_to_300_of_the_lines_of_the_occurred_risk_is_beside_250_not_in_variance(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Sur le projet dont le risque est survenu à 250, la réestimation à 300 des lignes qui en
    # sont issues présente 300 en regard de 250, et laisse l'écart de couverture à -190. » The line
    # of 170 reestimated to 220, the other staying at 80.
    ready = reassessed(api, project)
    occurred(ready, worker)
    current = in_current(ready)
    current.lines.changed(line_named(current, SEARCH), unit_disbursement="220.00")
    assert coverage(ready) == ("60.00", "0.00", "250.00", "300.00", "-190.00")


# --- After a merge ------------------------------------------------------------------------------


def merged_reading(
    ready: Occurring, current: Costed, worker: Worker, amendment: str
) -> tuple[Figures, dict[str, Any]]:
    """Merge a differential; give the coverage of the revision it marked, and the next revision.

    The revision that follows reads the coverage the same, and the budget of the reference the
    merge has just designated: the document the marking keeps holds the budget of the reference
    before it, the designation following the marking.
    """
    assert merged(ready.api, current, worker, amendment)["status"] == "succeeded"
    marked = coverage(ready, current.revision_id)
    following = ready.risks.revision()
    assert coverage(ready, following["revision_id"]) == marked
    return marked, following


@pytest.mark.requirement("WF-RIS-0050-A")
def test_an_amendment_that_does_not_touch_the_risks_leaves_the_reserve_at_60_and_the_variance(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « un avenant qui ne touche pas aux risques laisse la réserve à 60 et l'écart de couverture à
    # -190 » : opened after the occurrence, so that it is up to date.
    ready = reassessed(api, project)
    occurred(ready, worker)
    current = in_current(ready)
    amendment = opened_amendment(api, current)
    on(current.tree, amendment).made("Recette")
    marked, following = merged_reading(ready, current, worker, amendment)
    assert marked == OCCURRED
    assert budget(ready, following["revision_id"]) == Decimal("1000.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_an_amendment_that_integrates_the_lines_of_the_risk_takes_the_budget_to_1250(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « un avenant qui intègre au budget de référence les lignes de ce risque porte le budget de
    # référence à 1 250 et laisse la réserve à 60 et l'écart à -190 » : the two lines the
    # occurrence merged, at a budget of nought, priced at 150 and 100 by the differential.
    ready = reassessed(api, project)
    occurred(ready, worker)
    current = in_current(ready)
    amendment = opened_amendment(api, current)
    tree = on(current.tree, amendment)
    lines = Lines(tree)
    lines.changed(node_labelled(tree, SEARCH), unit_disbursement="150.00")
    lines.changed(node_labelled(tree, WIRES), unit_disbursement="100.00")
    marked, following = merged_reading(ready, current, worker, amendment)
    assert marked == OCCURRED
    assert budget(ready, following["revision_id"]) == Decimal("1250.00")


@pytest.mark.requirement("WF-RIS-0050-A")
@pytest.mark.story("US-3060")
def test_an_amendment_that_declares_a_risk_of_50_takes_the_reserve_to_110_and_the_variance_stays(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « un avenant qui déclare un nouveau risque de provision 50 porte la réserve à 110 et les
    # provisions restantes à 50, et laisse l'écart à -190 » : the risk declared after the opening of
    # the differential, which the update then brings up to date before it is merged (#4034).
    ready = reassessed(api, project)
    occurred(ready, worker)
    current = in_current(ready)
    amendment = opened_amendment(api, current)
    on(current.tree, amendment).made("Recette")
    declared = ready.risks.declared("0.5", "Grève des transporteurs")
    ready.risks.costed_at(declared, current.revision_id, "100.00")
    assert ready.risks.risk(declared)["provision_amount"] == "50.00"
    late = OutOfDate(current, amendment, on(current.tree, amendment))
    assert rebased(api, late).status_code == 200
    provision = f"Provision — {declared['label']}"
    assert line_named(current, provision)["estimate_line"]["budgeted_amount"] == "0.00"
    marked, following = merged_reading(ready, current, worker, amendment)
    assert marked == ("110.00", "50.00", "250.00", "250.00", "-190.00")
    # « Les lignes de provision ne font jamais partie du budget de référence » : the line of the
    # new risk bears the 50 the reference fixed, in the reference the merge marked and in the
    # revision copied from it, and the budget of the reference stays 1 000 (US-3060, #4274).
    after = in_current(replace(ready, revision=following))
    for each in (current, after):
        assert line_named(each, provision)["estimate_line"]["budgeted_amount"] == "50.00"
    assert budget(ready, following["revision_id"]) == Decimal("1000.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_reserve_accumulates_across_two_references(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la réserve de la nouvelle référence conserve la provision que portaient dans la précédente
    # les risques survenus ou écartés avant elle, et s'augmente de celle des risques identifiés
    # qu'elle porte »: the first merge makes a reference that keeps the 60 of the risk occurred, the
    # second, after a risk of 50 declared in the revision that follows, a reference of 110.
    ready = reassessed(api, project)
    occurred(ready, worker)
    first = in_current(ready)
    amendment = opened_amendment(api, first)
    on(first.tree, amendment).made("Recette")
    marked, following = merged_reading(ready, first, worker, amendment)
    assert marked == OCCURRED
    assert shares(ready, first.revision_id) == {UUID(ready.risk["risk_id"]): Decimal("60.00")}
    ready = replace(ready, revision=following)
    second = in_current(ready)
    declared = ready.risks.declared("0.5", "Grève des transporteurs")
    ready.risks.costed_at(declared, second.revision_id, "100.00")
    amendment = opened_amendment(api, second)
    on(second.tree, amendment).made("Réception")
    assert merged(api, second, worker, amendment, name="v3.0")["status"] == "succeeded"
    assert shares(ready, second.revision_id) == {
        UUID(ready.risk["risk_id"]): Decimal("60.00"),
        UUID(declared["risk_id"]): Decimal("50.00"),
    }
    assert coverage(ready, second.revision_id) == (
        "110.00",
        "50.00",
        "250.00",
        "250.00",
        "-190.00",
    )


# --- The remaining to commit after an amendment ------------------------------------------------


@pytest.mark.requirement("WF-RAE-0010-A")
def test_an_amendment_to_150_hours_counts_150_on_a_line_not_reestimated_and_keeps_140(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Après un avenant qui porte de 100 à 150 heures une ligne non réestimée d'une tâche non
    # démarrée, le reste à engager compte 150 heures ; une ligne réestimée à 140 avant l'avenant
    # garde 140. » The two lines of the making, not started; the second reestimated to 140 around
    # the service, as the entry of the remaining does.
    role = str(project.costs.role)
    making = node_labelled(project.tree, MAKING)
    for label in ("Soudure", "Câblage"):
        project.lines.made(making, label=label, quantity="1", resource_role_id=role, hours="100")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.label == "Câblage")
            .values(hours=Decimal(140), reestimated_at=utc_now())
        )
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    for label in ("Soudure", "Câblage"):
        Lines(tree).changed(node_labelled(tree, label), hours="150")
    assert merged(api, project, worker, amendment)["status"] == "succeeded"
    held = lines_of(project, project.structure_id)
    assert (held["Soudure"].hours, held["Câblage"].hours) == (Decimal(150), Decimal(140))
    # The remaining counts the 150 hours of the line not reestimated and the 140 kept, at the rate
    # of the role, beside the 1 000 of the two other lines.
    assert remaining(api, project, project.revision_id) == Decimal(1000) + (150 + 140) * Decimal(65)
