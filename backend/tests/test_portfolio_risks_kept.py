# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks a marking keeps for the portfolio, and what the risks give it besides (US-2680/L3).

The project of ``occurrence_support``: costed at 1 000, a risk of severity 200 at 30 % declared in
its first revision, marked and designated the reference, the second opened, which copies it; the
project moved In progress. ``store_contribution`` keeps the document ``portfolio_risks`` with the
other documents of the portfolio, at a marking as at the merge of a differential (EP-08, #4282);
the current day computes it the same, kept by the cache under a key the counters of the risks move
(#4158). The interface of the risks gives besides the outcomes of a period (``outcomes_between``)
and the risks not reviewed since an instant (``not_reviewed_since``).
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
from milestone_tracking_support import MILESTONE, START, TIME_TIME
from nodes_support import Tree, put_facts
from occurrence_support import SEARCH, Occurring, occurring
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from remaining_support import task_named
from risks_support import Costed, costed, material
from risks_support import occur as made_occurred
from sqlalchemy import select

from waterfall.core.indicators.contributions import contribution_key
from waterfall.core.indicators.interface import (
    PORTFOLIO_KINDS,
    Contributing,
    day_documents_of,
    kept_documents_of,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.planning.interface import milestone_forecasts
from waterfall.core.portfolio.contributing import DAY_KINDS, day_contribution
from waterfall.core.projects.interface import current_day, project_facts
from waterfall.core.resource_settings.interface import roles_stamp
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.interface import ReviewWindow, not_reviewed_since, outcomes_between
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
    occurred_risk = ready.risks.declared("0.4", "Panne de la grue")
    ready.risks.costed_at(occurred_risk, project.revision_id, "300.00")
    made_occurred(project.stage, occurred_risk["risk_id"], project.revision_id, "300.00")
    left = ready.risks.declared("0.2", "Gel des sols")
    ready.risks.reviewed(ready.risks.risk(left), state="dismissed")
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
    by_id = {each["risk_id"]: each for each in risks["risks"]}
    assert set(by_id) == {ready.risk["risk_id"], occurred_risk["risk_id"], left["risk_id"]}
    risk = by_id[ready.risk["risk_id"]]
    assert (risk["state"], risk["probability"], risk["severity"], risk["provision_amount"]) == (
        "identified",
        "0.3000",
        "200.00",
        "60.00",
    )
    assert by_id[occurred_risk["risk_id"]]["state"] == "occurred"
    assert by_id[left["risk_id"]]["state"] == "dismissed"
    # What the merge keeps is what the register gives once the revision is designated, and what
    # the day computes on it: neither the part of the reference before, nor a part unwritten yet.
    register = register_of(ready, project.revision_id)
    assert {key: figures(each) for key, each in by_id.items()} == {
        key: figures(register[key]) for key in by_id
    }
    with project.stage.database.transaction() as session:
        day = day_contribution(
            session, project_id=project.project_id, revision_id=project.revision_id, at=marked_at
        )
    assert day[RISKS] == risks


@pytest.mark.story("US-2680")
def test_the_merge_of_a_differential_dates_a_milestone_in_the_reference_it_becomes(
    ready: Occurring, worker: Worker
) -> None:
    # Propre à l'US : « la même fonction de calcul donne les mêmes documents » au jour courant
    # (#4282). A milestone tracked and dated in the current revision is unknown to the reference
    # before the merge; the merge designates its revision the reference at the instant it marks it,
    # so the date kept for the milestone is its forecast in that revision, as the day gives it
    # after, not none.
    project = current(ready)
    node = project.tree.made("Jalon de réception", task=MILESTONE)
    held = task_named(project.tree, "Jalon de réception")
    path = f"{project.tree.path}/nodes/{node['node_id']}/tracking"
    body = {"entries": [TIME_TIME], "lock_version": held["lock_version"]}
    answer = ready.api.put(path, headers=project.stage.manager.headers, json=body)
    assert answer.status_code == 200, answer.text
    put_facts(project.stage, node["node_id"], start_date=START, finish_date=START)
    amendment = opened_amendment(ready.api, project)
    branch = on(project.tree, amendment)
    task = branch.made("Extension")
    Lines(branch).made(task, **material(project.costs, "Matériel", "200.00"))
    assert merged(ready.api, project, worker, amendment)["status"] == "succeeded"
    kept = kept_of(project.stage.database, project.revision_id)
    with project.stage.database.transaction() as session:
        reference = project_facts(session, project.project_id).reference_revision_id
        marked_at = session.scalar(
            select(Revision.marked_at).where(Revision.id == project.revision_id)
        )
        assert marked_at is not None
        day = day_contribution(
            session, project_id=project.project_id, revision_id=project.revision_id, at=marked_at
        )
    assert reference == project.revision_id
    (milestone,) = kept["portfolio_milestones"]["milestones"]
    with project.stage.database.transaction() as session:
        lineage = UUID(milestone["lineage_id"])
        planned = milestone_forecasts(session, project.project_id, [lineage], [project.revision_id])
    assert milestone["reference_date"] == planned[project.revision_id][lineage].isoformat()
    assert day["portfolio_milestones"] == kept["portfolio_milestones"]


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
    ready: Occurring, cache: IndicatorsCache, worker: Worker
) -> None:
    # Propre à l'US : « l'empreinte sous laquelle le cache garde la contribution d'un projet couvre
    # ce que la contribution lit : […] les compteurs des risques ; un changement de l'une de ces
    # valeurs n'est pas servi d'après l'entrée ancienne » (#4158). The fingerprint of the day reads
    # them already: a review of the risk — its probability to 50 % — and a change of its label each
    # change the part of the day of the key, and the next reading computes the risks again; so do
    # the severity — a line added to its own estimate — and the occurrence, its state, then the
    # re-estimated amount of a line it merged.
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
    # The severity — the own estimate — and the occurrence: its state, then the re-estimated amount
    # of the lines it merged, each move the key as well.
    ready.risks.costed_at(ready.read(), revision_id, "100.00")
    keys.append(key())
    assert (read()["severity"], read()["provision_amount"]) == ("300.00", "150.00")
    assert counted.calls == 4
    occurred(ready, worker)
    keys.append(key())
    assert read()["state"] == "occurred"
    assert counted.calls == 5
    before = read()["occurred_reestimated_amount"]
    line = next(
        each
        for each in ready.main()
        if each["kind"] == "estimate_line" and each["estimate_line"]["label"] == SEARCH
    )
    answer = ready.api.patch(
        f"{ready.main_path()}/nodes/{line['node_id']}/estimate-line",
        headers=ready.risks.headers,
        json={"lock_version": line["lock_version"], "unit_disbursement": "500.00"},
    )
    assert answer.status_code == 200, answer.text
    keys.append(key())
    assert read()["occurred_reestimated_amount"] != before
    assert counted.calls == 6
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


def another_ready(ready: Occurring, api: ContractClient) -> Occurring:
    """Give a second project of the platform, its risk identified in its second revision too."""
    stage = ready.project.stage
    other = create(api, stage.manager, label="Extension du poste de commande")
    scene_two = replace(stage, project=other)
    second = occurring(api, costed(api, scene_two, ready.project.costs))
    path = f"{PROJECTS}/{second.project.project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-2680-B", "lock_version": counter}
    )
    assert coded.status_code == 200, coded.text
    return second


@pytest.mark.story("US-2680")
def test_the_outcomes_of_projects_are_ordered_and_a_risk_dismissed_keeps_its_share(
    ready: Occurring, api: ContractClient
) -> None:
    # Le lot : ``outcomes_between`` rend ses résultats « par projet, jour, risque ». A risk
    # identified in the reference then dismissed bears the share it held there, 60 — not none —;
    # two projects, each with a second risk declared and dismissed (no share), come out by project,
    # then day, then risk.
    second = another_ready(ready, api)
    expected: set[tuple[UUID, str, str, Decimal]] = set()
    for each, shares in ((ready, D("60.00")), (second, D("60.00"))):
        each.risks.reviewed(each.read(), state="dismissed")
        later = each.risks.declared("0.2", "Gel des sols")
        each.risks.reviewed(each.risks.risk(later), state="dismissed")
        expected |= {
            (each.project.project_id, each.risk["risk_id"], "dismissed", shares),
            (each.project.project_id, later["risk_id"], "dismissed", D("0.00")),
        }
    today = current_day(utc_now())
    with ready.project.stage.database.transaction() as session:
        read = outcomes_between(
            session, [ready.project.project_id, second.project.project_id], today, today
        )
    assert len(read) == 4
    assert {
        (each.project_id, str(each.risk_id), each.state, each.provision_amount) for each in read
    } == expected
    keys = [(each.project_id, each.reviewed_on, each.risk_id) for each in read]
    assert keys == sorted(keys)
    assert len({project for project, _, _ in keys}) == 2


@pytest.mark.story("US-2680")
def test_the_risks_not_reviewed_since_an_instant_are_the_identified_ones_the_revision_presents(
    ready: Occurring,
) -> None:
    # Le lot : ``not_reviewed_since`` donne « les risques identifiés non réexaminés depuis un
    # instant » (US-2750, ``risks_not_reviewed``), en peu de requêtes pour plusieurs projets
    # (#4294 point 1). The current revision presents the declaration of the risk, made in the first
    # one before its marking, and its confirmation made since: the risk is re-examined since an
    # instant before the declaration, and since the instant before the confirmation. The first
    # revision, marked, presents no review made after its marking. A risk reviewed dismissed is not
    # identified, and is not given.
    project_id = ready.project.project_id
    first, second = UUID(ready.first["revision_id"]), UUID(ready.revision["revision_id"])
    risk_id = UUID(ready.risk["risk_id"])
    since = utc_now()

    def not_reviewed(revision_id: UUID, instant: datetime) -> frozenset[UUID]:
        with ready.project.stage.database.transaction() as session:
            found = not_reviewed_since(session, {project_id: ReviewWindow(revision_id, instant)})
        return found.get(project_id, frozenset())

    assert not_reviewed(second, since) == {risk_id}
    assert not_reviewed(second, since - timedelta(days=1)) == frozenset()
    ready.risks.reviewed(ready.read())
    left = ready.risks.declared("0.2", "Gel des sols")
    ready.risks.reviewed(ready.risks.risk(left), state="dismissed")
    assert not_reviewed(second, since) == frozenset()
    assert not_reviewed(first, since) == {risk_id}
    assert not_reviewed(first, since - timedelta(days=1)) == frozenset()
