# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the portfolio on real risks: the current day, and the markings read (US-2730).

The project of ``occurrence_support``, costed at 1 000: a risk of 200 at 30 % in the reference
(reserve 60) — which occurs, its own estimate reassessed to 250 and its lines re-estimated to
300 —, and a second of 400 at 10 % (40) identified beside it, the project moved In progress. The
current day reads the risks of the revision of the day and their coverage as the project gives
them; once the revision is marked, the date asked reads what the marking kept, the same answer.
Every answer is validated against the contract by the client of the tests.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import node_labelled
from estimate_support import Lines, costing
from indicators_support import marked
from merges_support import client
from nodes_support import Tree
from occurrence_support import SEARCH, Occurring, occurring
from projects_support import PROJECTS
from projects_support import scene as make_scene
from risks_support import Costed, Risks, costed
from sqlalchemy import text, update

from waterfall.core.projects.interface import current_day
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
RISKS = "/api/v1/portfolio/risks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
LABEL = "Modernisation du poste de commande"
D = Decimal


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
    return Worker(
        database, queue, {"risk_occurrence": occur, "structure_merge": merge}, "worker", AT_ONCE
    )


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def ready(api: ContractClient, stage: Scene, worker: Worker) -> Occurring:
    """Give the project whose first risk has occurred and whose lines were re-estimated to 300.

    Its own estimate reassessed to 250 before the occurrence (the cost at occurrence), the line of
    170 re-estimated to 220 after it; the project In progress, a second risk of 40 identified.
    """
    project: Costed = costed(api, stage, costing(stage.database))
    other = Risks(api, project).declared("0.1", "Panne de la grue")
    Risks(api, project).costed_at(other, project.revision_id, "400.00")
    ready = occurring(api, project)
    line = next(
        each
        for each in ready.own()
        if each["kind"] == "estimate_line" and each["estimate_line"]["label"] == SEARCH
    )
    ready.risks.repriced(ready.risk, ready.revision["revision_id"], line, "170.00")
    path = f"{PROJECTS}/{project.project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-2730", "lock_version": counter}
    )
    assert coded.status_code == 200, coded.text
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": report["creates_current_revision"],
    }
    answer = api.post(f"{ready.path}/occurrence", headers=ready.risks.headers, json=sent)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers)
    assert task.json()["status"] == "succeeded", task.text
    tree = Tree(api, stage, ready.revision)
    Lines(tree).changed(node_labelled(tree, SEARCH), unit_disbursement="220.00")
    return ready


def read(ready: Occurring, query: str = "") -> dict[str, Any]:
    """Read the risks of the portfolio as the reader of the portfolio does."""
    answer = ready.api.get(f"{RISKS}{query}", headers=ready.project.stage.reader.headers)
    assert answer.status_code == 200, answer.text
    body: dict[str, Any] = answer.json()
    return body


def own_coverage(ready: Occurring) -> dict[str, Any]:
    """Read the coverage of the project in its current revision, as its manager does."""
    path = f"{PROJECTS}/{ready.project.project_id}/risks/coverage"
    answer = ready.api.get(path, headers=ready.risks.headers)
    assert answer.status_code == 200, answer.text
    body: dict[str, Any] = answer.json()
    return {name: body[name] for name in sorted(body) if name != "context"}


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_current_day_reads_the_risks_and_the_coverage_of_the_project_as_it_gives_them(
    ready: Occurring,
) -> None:
    # « Le total des provisions identifiées égale la somme des provisions des risques identifiés »
    # : the risk that occurred is out of it, the second one, 40, is the whole total and the
    # heaviest, with its project; the matrix counts it once, at 40 % of the 1 000 of the budget and
    # 10 % of probability. « … la couverture rend, à côté du coût des survenus, la somme des
    # réestimés » :
    # the cost at occurrence, 250, and the lines re-estimated, 300, differ (#2002), and the
    # coverage is the project's own, its variance counting the 250 — 100 - (40 + 250).
    body = read(ready)
    assert body["scope"]["project_count"] == 1
    assert body["identified_total"] == "40.00"
    assert [
        (each["label"], each["project_label"], each["can_open"], each["provision_amount"])
        for each in body["heaviest"]
    ] == [("Panne de la grue", LABEL, True, "40.00")]
    cells = {
        (each["probability_level"], each["severity_level"]): each["count"]
        for each in body["matrix"]["cells"]
    }
    assert {key for key, count in cells.items() if count} == {(1, 4)}
    (point,) = body["matrix"]["points"]
    assert point["severity_ratio"] == {"is_computable": True, "value": "0.4", "reason": None}
    assert (point["probability"], point["severity_amount"], point["state"]) == (
        "0.1",
        "400.00",
        "identified",
    )
    assert body["coverage"] == {
        "reserve": "100.00",
        "remaining_provisions": "40.00",
        "occurred_cost": "250.00",
        "occurred_reestimated": "300.00",
        "coverage_variance": "-190.00",
    }
    assert body["coverage"] == own_coverage(ready)
    assert body["matrix"]["totals"] == {
        "identified": "40.00",
        "occurred": "60.00",
        "dismissed": "0.00",
        "total": "100.00",
        "reserve": "100.00",
    }


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_period_outcome_sums_the_provisions_of_the_risks_that_changed_state_in_the_period(
    ready: Occurring,
) -> None:
    # Propre à l'US : « period_outcome somme, sur la période, les provisions des risques survenus
    # et celles des risques écartés, par la date du réexamen qui les a fait changer d'état » : the
    # risk occurred today bears the share it held in the reference, 60; the second risk, dismissed
    # today, held 40 there. A period of last January holds neither.
    assert read(ready)["period_outcome"] == {
        "occurred_provisions": "60.00",
        "dismissed_provisions": "0.00",
    }
    other = next(
        each
        for each in ready.api.get(f"{ready.risks.base}/risks", headers=ready.risks.headers).json()[
            "items"
        ]
        if each["label"] == "Panne de la grue"
    )
    ready.risks.reviewed(other, state="dismissed")
    body = read(ready)
    assert body["period_outcome"] == {
        "occurred_provisions": "60.00",
        "dismissed_provisions": "40.00",
    }
    assert body["identified_total"] == "0.00"
    assert body["coverage"]["coverage_variance"] == "-150.00"
    earlier = read(ready, "?from=2026-01-01&to=2026-01-31")
    assert earlier["period_outcome"] == {
        "occurred_provisions": "0.00",
        "dismissed_provisions": "0.00",
    }


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_a_date_asked_reads_what_the_marking_kept_and_the_same_answer_as_the_day_after_it(
    ready: Occurring,
) -> None:
    # Propre à l'US : « à une date passée, la vue lit les risques que les révisions marquées ont
    # conservés » : the revision marked, the day reads it as its last marked, and the date asked —
    # today, a date asked — reads the documents the marking kept: the two answers are one.
    marked(ready.project.stage, ready.revision, "v2")
    day = read(ready)
    asked = read(ready, f"?as_of={current_day(utc_now())}")
    assert asked == day
    assert asked["identified_total"] == "40.00"
    assert asked["coverage"]["occurred_reestimated"] == "300.00"
    assert asked["coverage"]["occurred_cost"] == "250.00"


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_at_a_past_date_the_outcomes_and_the_reserve_follow_the_reference_of_the_day(
    ready: Occurring, owner: Engine
) -> None:
    # Constat de #4294 : ``outcomes_between`` ne vient d'aucun document conservé — la provision
    # d'une issue est la part du risque dans la référence actuelle (WF-RIS-0040) —, et la réserve
    # est celle que la référence conserve (``kept_coverage``). Le matrice, elle, garde ce que le
    # marquage a conservé. The share the occurred risk bears in the reference moved from 60 to 75
    # after the marking: the date asked gives 75 and a reserve of 115, the matrix 60 as kept.
    marked(ready.project.stage, ready.revision, "v2")
    query = f"?as_of={current_day(utc_now())}"
    before = read(ready, query)
    assert before["period_outcome"]["occurred_provisions"] == "60.00"
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            update(RiskReferenceShare)
            .where(
                RiskReferenceShare.risk_id == UUID(ready.risk["risk_id"]),
                RiskReferenceShare.revision_id == UUID(ready.first["revision_id"]),
            )
            .values(provision_amount=D("75.00"))
        )
    after = read(ready, query)
    assert after["period_outcome"]["occurred_provisions"] == "75.00"
    assert after["coverage"]["reserve"] == "115.00"
    assert after["coverage"]["coverage_variance"] == "-175.00"
    assert after["matrix"]["totals"]["occurred"] == "60.00"
    assert after["identified_total"] == before["identified_total"] == "40.00"
