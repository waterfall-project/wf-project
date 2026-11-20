# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks a marking keeps for the portfolio, and what the risks give it besides (US-2680/L3).

The project of ``occurrence_support``: costed at 1 000, a risk of severity 200 at 30 % declared in
its first revision, marked and designated the reference, the second opened, which copies it; the
project moved In progress. ``store_contribution`` keeps the document ``portfolio_risks`` with the
other documents of the portfolio, at a marking as at the merge of a differential (EP-08, #4282);
the current day computes it the same, kept by the cache under a key the counters of the risks move
(#4158). The interface of the risks gives besides the outcomes of a period (``outcomes_between``)
and the risks reviewed since an instant (``reviewed_since``).
"""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import on, opened_amendment
from estimate_support import Lines, costing
from indicators_support import marked
from merges_support import client, merged
from nodes_support import Tree
from occurrence_support import Occurring, occurring
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import Costed, costed, material
from sqlalchemy import select

from waterfall.core.indicators.contributions import contribution_key
from waterfall.core.indicators.interface import (
    PORTFOLIO_KINDS,
    Contributing,
    day_documents_of,
    kept_documents_of,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.portfolio.contributing import DAY_KINDS, day_contribution
from waterfall.core.projects.interface import current_day
from waterfall.core.resource_settings.interface import roles_stamp
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.interface import outcomes_between, reviewed_since
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.database import utc_now
from waterfall.worker.merge import merge
from waterfall.worker.occurrence import occur
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from datetime import date, datetime

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
RISKS = "portfolio_risks"
# What a marking of a project In progress keeps for the portfolio (EP-11, "Tables et migrations").
PROJECT_KINDS = {"portfolio_workload", "portfolio_cost_structure", RISKS, "portfolio_milestones"}
# The validity of an entry of the cache in these tests, in seconds.
TTL = 300
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
    runs = {"risk_occurrence": occur, "structure_merge": merge}
    return Worker(database, queue, runs, "worker", AT_ONCE)


@pytest.fixture
def ready(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Occurring:
    """Give the risk identified in the second revision of the project, moved In progress."""
    stage: Scene = make_scene(api, owner, database, realm)
    ready = occurring(api, costed(api, stage, costing(stage.database)))
    path = f"{PROJECTS}/{ready.project.project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-2680", "lock_version": counter}
    )
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    return ready


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[IndicatorsCache]:
    """Give the cache of the indicators beside the queue of the test; its entries deleted after."""
    opened = IndicatorsCache.of(queue, TTL)
    yield opened
    held: Any = queue.client
    for key in held.scan_iter(match=f"{PREFIX}*"):
        held.delete(key)
    opened.close()


def occurred(ready: Occurring, worker: Worker) -> None:
    """Confirm the occurrence of the risk as its report was read, and have the worker run it."""
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


def three_states(ready: Occurring, worker: Worker) -> dict[str, dict[str, Any]]:
    """Give the project a risk in each state, in its current revision; give them by state.

    The risk of the fabrics occurs; a second, declared at 50 % with an own estimate of 100, stays
    identified; a third, declared then reviewed dismissed, holds no share in the reference.
    """
    occurred(ready, worker)
    revision_id = ready.revision["revision_id"]
    held = ready.risks.declared("0.5", "Grève des transporteurs")
    ready.risks.costed_at(held, revision_id, "100.00")
    left = ready.risks.declared("0.2", "Gel des sols")
    ready.risks.reviewed(ready.risks.risk(left), state="dismissed")
    return {
        "occurred": ready.read(),
        "identified": ready.risks.risk(held),
        "dismissed": ready.risks.risk(left),
    }


def kept_of(database: Database, revision_id: UUID) -> Mapping[IndicatorKind, Document]:
    """Read every document of the portfolio a marked revision kept, by kind."""
    with database.transaction() as session:
        return kept_documents_of(session, [revision_id], sorted(PORTFOLIO_KINDS))[revision_id]


def register_of(ready: Occurring, revision_id: object) -> dict[str, dict[str, Any]]:
    """Read the register of the risks of a revision, as its manager does; give the risks by id."""
    path = f"{PROJECTS}/{ready.project.project_id}/risks?revision_id={revision_id}"
    answer = ready.api.get(path, headers=ready.risks.headers)
    assert answer.status_code == 200, answer.text
    return {each["risk_id"]: each for each in answer.json()["items"]}


def figures(risk: Mapping[str, Any]) -> tuple[object, ...]:
    """Give what the portfolio keeps of a risk, its amounts as decimals, null as null."""
    amounts = ("probability", "severity", "provision_amount", "occurrence_cost")
    numbers = tuple(None if risk[key] is None else D(risk[key]) for key in amounts)
    reestimated = risk["occurred_reestimated_amount"]
    return (*numbers, None if reestimated is None else D(reestimated), risk["state"], risk["label"])


# --- What the marking keeps ----------------------------------------------------------------------


@pytest.mark.story("US-2680")
def test_the_marking_keeps_for_each_risk_its_probability_its_severity_its_provision_its_state(
    ready: Occurring, worker: Worker
) -> None:
    # Propre à l'US : « le marquage conserve de plus, pour le projet : […] pour chaque risque, sa
    # probabilité, sa gravité, sa provision et son état » — with the cost at occurrence and the
    # re-estimated amount of an occurred one, and the base of the project, the budget of the
    # reference, 1 000. Each risk is kept in the order of its declaration, as the register reads it
    # in the revision marked: the identified one at its severity weighted, 50; the occurred one at
    # the share it held in the reference, 60, and its cost at occurrence, 200; the dismissed one at
    # the share it held, none.
    states = three_states(ready, worker)
    marked_at = marked(ready.project.stage, ready.revision, "v2")
    revision_id = UUID(ready.revision["revision_id"])
    kept = kept_of(ready.project.stage.database, revision_id)
    assert set(kept) == PROJECT_KINDS
    document = kept[RISKS]
    assert document["base"] == "1000.00"
    risks = document["risks"]
    assert [each["risk_id"] for each in risks] == [
        states[state]["risk_id"] for state in ("occurred", "identified", "dismissed")
    ]
    register = register_of(ready, revision_id)
    for each in risks:
        assert figures(each) == figures(register[each["risk_id"]])
    by_state = {each["state"]: each for each in risks}
    identified, occurring_, dismissed = (
        by_state[state] for state in ("identified", "occurred", "dismissed")
    )
    assert (identified["probability"], identified["severity"]) == ("0.5000", "100.00")
    assert identified["provision_amount"] == "50.00"
    assert identified["occurrence_cost"] is None
    assert identified["occurred_reestimated_amount"] is None
    assert (occurring_["provision_amount"], occurring_["occurrence_cost"]) == ("60.00", "200.00")
    assert occurring_["occurred_reestimated_amount"] is not None
    assert (dismissed["provision_amount"], dismissed["occurrence_cost"]) == ("0.00", None)
    with ready.project.stage.owner.connect() as connection:
        instants = connection.execute(
            select(RevisionIndicator.computed_at).where(
                RevisionIndicator.revision_id == revision_id, RevisionIndicator.kind == RISKS
            )
        ).all()
    assert instants == [(marked_at,)]


def current(ready: Occurring) -> Costed:
    """Give the project costed as it stands in its current revision, the second."""
    tree = Tree(ready.api, ready.project.stage, ready.revision)
    return replace(
        ready.project,
        tree=tree,
        lines=Lines(tree),
        revision_id=UUID(ready.revision["revision_id"]),
        structure_id=UUID(tree.structure_id),
    )


@pytest.mark.story("US-2680")
def test_the_merge_of_a_differential_keeps_every_document_of_the_portfolio_risks_included(
    ready: Occurring, worker: Worker
) -> None:
    # Propre à l'US : « la fusion d'un différentiel (EP-08), qui marque, les conserve de même »
    # (#4282). A differential of the current revision adds a task of 200 and is merged: the
    # revision the merge marks keeps every document of a project In progress, at the instant of
    # its marking, and its risk is related to the budget of the reference it becomes at that
    # instant, 1 200, not to the one before, 1 000.
    project = current(ready)
    amendment = opened_amendment(ready.api, project)
    branch = on(project.tree, amendment)
    task = branch.made("Extension")
    Lines(branch).made(task, **material(project.costs, "Matériel", "200.00"))
    assert merged(ready.api, project, worker, amendment)["status"] == "succeeded"
    kept = kept_of(project.stage.database, project.revision_id)
    assert set(kept) == PROJECT_KINDS
    with project.stage.owner.connect() as connection:
        marked_at = connection.scalar(
            select(Revision.marked_at).where(Revision.id == project.revision_id)
        )
        rows = connection.execute(
            select(RevisionIndicator.kind, RevisionIndicator.computed_at).where(
                RevisionIndicator.revision_id == project.revision_id,
                RevisionIndicator.kind.in_(sorted(PORTFOLIO_KINDS)),
            )
        )
        instants = {(kind, at) for kind, at in rows}
    assert marked_at is not None
    assert instants == {(kind, marked_at) for kind in PROJECT_KINDS}
    assert kept["portfolio_cost_structure"]["budget_revision_id"] == str(project.revision_id)
    risks = kept[RISKS]
    assert risks["base"] == "1200.00"
    (risk,) = risks["risks"]
    assert (risk["risk_id"], risk["state"]) == (ready.risk["risk_id"], "identified")
    assert (risk["probability"], risk["severity"], risk["provision_amount"]) == (
        "0.3000",
        "200.00",
        "60.00",
    )


# --- The current day, and the key of the cache ---------------------------------------------------


class Counted:
    """The contribution of the day of the portfolio, which counts the projects it computes."""

    def __init__(self) -> None:
        """Count none yet."""
        self.calls = 0

    def __call__(
        self, session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
    ) -> Mapping[IndicatorKind, Document]:
        self.calls += 1
        return day_contribution(session, project_id=project_id, revision_id=revision_id, at=at)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_change_of_a_risk_is_not_served_from_the_entry_of_the_contribution_before(
    ready: Occurring, cache: IndicatorsCache
) -> None:
    # Propre à l'US : « l'empreinte sous laquelle le cache garde la contribution d'un projet couvre
    # ce que la contribution lit : […] les compteurs des risques ; un changement de l'une de ces
    # valeurs n'est pas servi d'après l'entrée ancienne » (#4158). The fingerprint of the day reads
    # them already: a review of the risk — its probability to 50 % — and a change of its label each
    # change the part of the day of the key, and the next reading computes the risks again.
    project_id = ready.project.project_id
    revision_id = UUID(ready.revision["revision_id"])
    at = utc_now()
    counted = Counted()

    def read() -> dict[str, Any]:
        with ready.project.stage.database.transaction() as session:
            found = day_documents_of(
                session, {project_id: revision_id}, at, Contributing(counted, DAY_KINDS), cache
            )
        (risk,) = found[project_id][RISKS]["risks"]
        return risk

    def key() -> str:
        with ready.project.stage.database.transaction() as session:
            return contribution_key(session, project_id, revision_id, at, roles_stamp(session))

    assert (read()["probability"], read()["provision_amount"]) == ("0.3000", "60.00")
    assert counted.calls == 1
    keys = [key()]
    ready.risks.reviewed(ready.read(), probability="0.5")
    keys.append(key())
    assert (read()["probability"], read()["provision_amount"]) == ("0.5000", "100.00")
    assert counted.calls == 2
    answer = ready.risks.update(ready.read(), label="Retard du fournisseur principal")
    assert answer.status_code == 200, answer.text
    keys.append(key())
    assert read()["label"] == "Retard du fournisseur principal"
    assert counted.calls == 3
    days = [each.split(":portfolio:")[0] for each in keys]
    assert len(set(days)) == len(days)


# --- The outcomes of a period, and the risks reviewed --------------------------------------------


@pytest.mark.story("US-2680")
def test_the_outcomes_of_a_period_are_the_risks_a_review_moved_with_their_share_in_the_reference(
    ready: Occurring, worker: Worker
) -> None:
    # Le lot : ``outcomes_between`` donne « les provisions survenues et écartées d'une période, par
    # la date du réexamen qui les a fait changer d'état » (US-2730, ``period_outcome``). The risk
    # occurred bears the share it held in the reference, 60; the one dismissed, never in the
    # reference, none; the one identified is no outcome. A review that confirms the dismissed one
    # changes no state and adds none; a period that ends before the day, or starts after it, holds
    # none.
    states = three_states(ready, worker)
    project_id = ready.project.project_id
    today = current_day(utc_now())
    day = timedelta(days=1)

    def found(first: date, last: date) -> set[tuple[str, date, str, Decimal]]:
        with ready.project.stage.database.transaction() as session:
            read = outcomes_between(session, [project_id], first, last)
        return {
            (str(each.risk_id), each.reviewed_on, each.state, each.provision_amount)
            for each in read
        }

    expected = {
        (states["occurred"]["risk_id"], today, "occurred", D("60.00")),
        (states["dismissed"]["risk_id"], today, "dismissed", D("0.00")),
    }
    assert found(today, today) == expected
    ready.risks.reviewed(ready.risks.risk(states["dismissed"]))
    assert found(today - day, today + day) == expected
    assert found(today - 2 * day, today - day) == set()
    assert found(today + day, today + 2 * day) == set()
    with ready.project.stage.database.transaction() as session:
        assert outcomes_between(session, [], today, today) == []


@pytest.mark.story("US-2680")
def test_the_risks_reviewed_since_an_instant_are_the_identified_ones_the_revision_presents(
    ready: Occurring,
) -> None:
    # Le lot : ``reviewed_since`` donne « les risques identifiés réexaminés depuis un instant »
    # (US-2750, ``risks_not_reviewed``). The current revision presents the declaration of the risk,
    # made in the first one before its marking, and its confirmation made since: the risk is
    # reviewed since an instant before the declaration, and since the instant before the
    # confirmation. The first revision, marked, presents no review made after its marking. A risk
    # reviewed dismissed is not identified, and is not given.
    project_id = ready.project.project_id
    first, second = UUID(ready.first["revision_id"]), UUID(ready.revision["revision_id"])
    risk_id = UUID(ready.risk["risk_id"])
    since = utc_now()

    def reviewed(revision_id: UUID, instant: datetime) -> frozenset[UUID]:
        with ready.project.stage.database.transaction() as session:
            return reviewed_since(session, project_id, revision_id, instant)

    assert reviewed(second, since) == frozenset()
    assert reviewed(second, since - timedelta(days=1)) == {risk_id}
    ready.risks.reviewed(ready.read())
    left = ready.risks.declared("0.2", "Gel des sols")
    ready.risks.reviewed(ready.risks.risk(left), state="dismissed")
    assert reviewed(second, since) == {risk_id}
    assert reviewed(first, since) == frozenset()
    assert reviewed(first, since - timedelta(days=1)) == {risk_id}
