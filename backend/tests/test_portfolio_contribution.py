# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a marking keeps for the portfolio, and what the current day gives the same (US-2680/L2).

``store_contribution``, registered after the indicators, keeps in the transaction of the marking the
documents of the portfolio the state of the project calls for: a project In progress its workload,
the structure of its costs and its tracked milestones; an offer its workload and the structure of
its costs on its estimate, and its curves. An exception of their computation fails the marking
whole. The current day computes the same documents by the same function, kept by the cache of the
indicators under a key that covers the probability of winning and the roles (#4158). The projects
are those of the fabrics of the portfolio (``portfolio_support``), and a project of a scene.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import Costing, Lines, add_role, costing
from indicators_support import clock_setter, marked
from milestone_tracking_support import DELIVERY, START, STUDIES, TIME_TIME, Project
from nodes_support import Tree
from portfolio_support import (
    OFFER,
    OFFERS_MARKED,
    READ_ON,
    REVIEW,
    REVIEW_MARKED,
    Portfolio,
    portfolio,
)
from project_rows import drop_every_partition, insert_project, partitioned_projects
from projects_support import MANAGING, PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import line_named
from sqlalchemy import event, func, select, text, update

from waterfall.core.cost_settings.tables import CostType
from waterfall.core.estimate.interface import offer_workload, portfolio_totals
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.indicators.contributions import contribution_key
from waterfall.core.indicators.interface import (
    PORTFOLIO_KINDS,
    Contributing,
    day_documents_of,
    kept_documents_of,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.planning.interface import milestone_forecasts, tasks_for_indicators
from waterfall.core.portfolio import contributing
from waterfall.core.portfolio.contributing import DAY_KINDS, day_contribution
from waterfall.core.projects.interface import (
    ProjectChange,
    Viewer,
    project_facts,
    stored_lock_version,
    update_project,
)
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    WeeklyHours,
    read_calendar,
    read_role,
    roles_stamp,
    set_role_activation,
    update_calendar,
)
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.interface import create_revision, load_marking, mark_revision
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from indicators_support import Clock
    from realm import TestRealm
    from redis import Redis
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

WORKLOAD, COST_STRUCTURE = "portfolio_workload", "portfolio_cost_structure"
MILESTONES, OFFER_CURVES = "portfolio_milestones", "portfolio_offer_curves"
RISKS = "portfolio_risks"
# The kinds of the portfolio a marking keeps: of a project In progress, of an offer, and all.
PROJECT_KINDS = (WORKLOAD, COST_STRUCTURE, RISKS, MILESTONES)
OFFER_KINDS = (WORKLOAD, COST_STRUCTURE, RISKS, OFFER_CURVES)
KEPT_HERE = (WORKLOAD, COST_STRUCTURE, RISKS, MILESTONES, OFFER_CURVES)
# The validity of an entry of the cache in these tests, in seconds.
TTL = 300
# The instant of the readings of the day: the date of the witness, after every fact of the fabrics.
AT = datetime(READ_ON.year, READ_ON.month, READ_ON.day, 9, 0, tzinfo=UTC)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def fabrics(api: ContractClient, stage: Scene) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of the scene."""
    return portfolio(api, stage)


def kept_of(database: Database, revision_id: UUID) -> dict[IndicatorKind, Document]:
    """Read every document of the scope of the project a marked revision kept, by kind."""
    kinds: list[IndicatorKind] = ["project", "estimate", *sorted(PORTFOLIO_KINDS)]
    with database.transaction() as session:
        return kept_documents_of(session, [revision_id], kinds)[revision_id]


def instants_of(owner: Engine, revision_id: UUID) -> set[tuple[str, datetime, datetime]]:
    """Read the kind, ``computed_at`` and ``created_at`` of the documents of the portfolio kept."""
    with owner.connect() as connection:
        rows = connection.execute(
            select(
                RevisionIndicator.kind, RevisionIndicator.computed_at, RevisionIndicator.created_at
            ).where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind.in_(sorted(PORTFOLIO_KINDS)),
            )
        )
        return {(kind, computed, created) for kind, computed, created in rows}


def amounts(entries: list[dict[str, str]], key: str) -> dict[str, Decimal]:
    """Give the amounts of a list of a structure of the costs, by its key."""
    return {each[key]: Decimal(each["amount"]) for each in entries}


def hours_of(workload: Document) -> dict[str, Decimal]:
    """Give the hours of each role of a document of the workload, its months summed."""
    return {
        role["resource_role_id"]: sum(
            (Decimal(each["hours"]) for each in role["months"]), Decimal(0)
        )
        for role in workload["roles"]
    }


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def mark(stage: Scene, revision_id: UUID, act: Act) -> None:
    """Mark a revision at an act, by the transaction of the worker."""
    with logging_context(correlation_id="marking"), stage.database.transaction() as session:
        mark_revision(session, revision_id, "v1.0", None, act)


# --- What the marking keeps ----------------------------------------------------------------------


@pytest.mark.story("US-2680")
def test_the_review_of_a_project_in_progress_keeps_its_workload_its_costs_and_its_milestones(
    fabrics: Portfolio,
) -> None:
    # Propre à l'US : « le marquage conserve de plus, pour le projet : la charge par rôle de
    # ressource et par mois — sur le reste à engager d'un projet en cours — ; les totaux par nature
    # de coût du budget de référence, hors lignes de provision, et du reste à engager, provisions
    # comprises, et la main-d'œuvre » ; « ces documents sont calculés à l'instant du marquage et
    # écrits dans sa transaction ». The review keeps its eight hours of the role, the budget of its
    # reference — the offer it was designated from — and its remaining, both its line of material
    # and its labour; no milestone is tracked. No curves of an offer: it is a project.
    running = fabrics.in_progress
    review, offer = running.marked[REVIEW][0], running.marked[OFFER][0]
    kept = kept_of(fabrics.stage.database, review)
    assert set(kept) == {"project", "estimate", *PROJECT_KINDS}
    assert hours_of(kept[WORKLOAD]) == {str(fabrics.costs.role): Decimal("8.00")}
    costs = kept[COST_STRUCTURE]
    assert costs["budget_revision_id"] == str(offer)
    budget = amounts(costs["budget_by_cost_type"], "cost_type_id")
    assert amounts(costs["remaining_by_cost_type"], "cost_type_id") == budget
    assert sorted(each["label"] for each in costs["budget_by_cost_type"]) == sorted(
        each["label"] for each in costs["remaining_by_cost_type"]
    )
    assert Decimal("1000.00") in budget.values()
    total = Decimal(kept["estimate"]["total"]["value"])
    assert sum(budget.values(), Decimal(0)) == total
    labour = amounts(costs["budget_labour_by_role"], "resource_role_id")
    assert set(labour) == {str(fabrics.costs.role)}
    assert labour[str(fabrics.costs.role)] == total - Decimal("1000.00")
    assert amounts(costs["remaining_labour_by_role"], "resource_role_id") == labour
    assert kept[MILESTONES] == {"milestones": []}
    # No risk is declared: the risks are kept all the same, none, on the budget of the reference.
    assert kept[RISKS] == {"base": f"{total:.2f}", "risks": []}
    assert instants_of(fabrics.stage.owner, review) == {
        (kind, REVIEW_MARKED, REVIEW_MARKED) for kind in PROJECT_KINDS
    }


@pytest.mark.requirement("WF-DAT-0040-A")
def test_an_offer_marked_keeps_its_estimate_for_the_portfolio_without_any_indicator_of_a_project(
    fabrics: Portfolio,
) -> None:
    # « Le marquage d'une offre, sur un projet en chiffrage, aboutit et conserve le total du devis
    # sans aucun indicateur projet. » : l'offre marquée conserve de plus ce que le portefeuille lit
    # d'une offre — its workload and the structure of its costs on its estimate, which stands for
    # the budget and for the remaining, and its curves, kept as a marking keeps them —, and nothing
    # that asks for a reference: no milestone.
    offer = fabrics.offer.marked[OFFER][0]
    kept = kept_of(fabrics.stage.database, offer)
    assert set(kept) == {"estimate", *OFFER_KINDS}
    assert hours_of(kept[WORKLOAD]) == {str(fabrics.costs.role): Decimal("8.00")}
    costs = kept[COST_STRUCTURE]
    assert costs["budget_revision_id"] == str(offer)
    total = Decimal(kept["estimate"]["total"]["value"])
    budget = amounts(costs["budget_by_cost_type"], "cost_type_id")
    assert sum(budget.values(), Decimal(0)) == total
    assert amounts(costs["remaining_by_cost_type"], "cost_type_id") == budget
    curves = kept[OFFER_CURVES]
    assert set(curves) == {"cost_curve", "cost_curve_payment_delays"}
    for curve in curves.values():
        assert curve["context"]["revision_id"] == str(offer)
        assert curve["context"]["revision_status"] == "marked"
        assert curve["context"]["is_stored"] is True
        assert curve["context"]["computed_at"] == "2026-02-16T09:00:00Z"
        named = {each["name"]: each for each in curve["series"]}
        assert named["actual_cost"]["points"] == []
    assert instants_of(fabrics.stage.owner, offer) == {
        (kind, OFFERS_MARKED, OFFERS_MARKED) for kind in OFFER_KINDS
    }


@pytest.fixture
def offer(api: ContractClient, stage: Scene) -> tuple[UUID, Costing]:
    """Give the current revision of an offer: eight hours of the role, 1 000 of material, 50 more.

    The provision is a line of material whose category is changed to provision around the
    service, as the risks of EP-08 write it.
    """
    costs = costing(stage.database)
    revision = open_revision(api, stage)
    tree = Tree(api, stage, revision)
    lines = Lines(tree)
    task = tree.made("Études")
    lines.made(task, quantity="1", resource_role_id=str(costs.role), hours="8")
    material = {"quantity": "1", "cost_category_id": str(costs.material)}
    lines.made(task, label="Matériel", unit_disbursement="1000.00", **material)
    lines.made(task, label="Aléa", unit_disbursement="50.00", **material)
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(line_named(tree, "Aléa")["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    return UUID(revision["revision_id"]), costs


@pytest.mark.story("US-2680")
def test_the_estimate_of_an_offer_stands_for_its_budget_without_provisions_and_its_remaining_with(
    stage: Scene, offer: tuple[UUID, Costing]
) -> None:
    # Propre à l'US : « les totaux par nature de coût du budget de référence, hors lignes de
    # provision, et du reste à engager, provisions comprises » ; pour une offre, son devis tient
    # lieu des deux (WF-PTF-0080). The provision line of 50 adds nothing to the budget, and 50 to
    # the remaining, under the nature of its category; the labour is the same in both.
    revision_id, _ = offer
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        totals = portfolio_totals(session, project_id, revision_id)
    assert totals.budget_revision_id == revision_id
    added = {
        key: amount - totals.budget_by_cost_type.get(key, Decimal(0))
        for key, amount in totals.remaining_by_cost_type.items()
    }
    assert sorted(added.values()) == [Decimal(0), Decimal(0), Decimal("50.00")]
    assert Decimal("1000.00") in totals.budget_by_cost_type.values()
    assert len(totals.budget_by_cost_type) == len(totals.remaining_by_cost_type) - 1
    assert totals.budget_labour_by_role == totals.remaining_labour_by_role
    assert set(totals.budget_cost_type_labels) == set(totals.budget_by_cost_type)
    assert set(totals.remaining_cost_type_labels) == set(totals.remaining_by_cost_type)
    act = Act(stage.manager.user_id, utc_now())
    mark(stage, revision_id, act)
    kept = kept_of(stage.database, revision_id)[COST_STRUCTURE]
    remaining = amounts(kept["remaining_by_cost_type"], "cost_type_id")
    assert remaining == {str(key): value for key, value in totals.remaining_by_cost_type.items()}
    budget = amounts(kept["budget_by_cost_type"], "cost_type_id")
    assert budget == {str(key): value for key, value in totals.budget_by_cost_type.items()}


@pytest.mark.story("US-2680")
def test_an_offer_marked_after_its_task_keeps_its_hours_on_the_months_of_the_task(
    stage: Scene, offer: tuple[UUID, Costing]
) -> None:
    # Propre à l'US : le marquage conserve « la charge par rôle de ressource et par mois — sur le
    # reste à engager d'un projet en cours, sur le devis d'une offre » (EP-11, « Tables et
    # migrations », ``portfolio_workload``). The task of the offer finishes seventy days before its
    # marking: its eight hours stay on the months of the task, none on the month of the marking,
    # where a remaining to commit would have put them whole.
    revision_id, costs = offer
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        tasks = tasks_for_indicators(session, project_id, revision_id)
    (task,) = [each for each in tasks if each.label == "Études"]
    months = {f"{each:%Y-%m}" for each in (task.start.day, task.finish.day)}
    marked_on = task.finish.day + timedelta(days=70)
    instant = datetime(marked_on.year, marked_on.month, marked_on.day, 9, 0, tzinfo=UTC)
    mark(stage, revision_id, Act(stage.manager.user_id, instant))
    (role,) = kept_of(stage.database, revision_id)[WORKLOAD]["roles"]
    assert role["resource_role_id"] == str(costs.role)
    held = {each["month"]: Decimal(each["hours"]) for each in role["months"]}
    assert set(held) <= months
    assert f"{marked_on:%Y-%m}" not in held
    assert sum(held.values(), Decimal(0)) == Decimal("8.00")


@pytest.mark.story("US-2680")
def test_an_offer_read_on_a_day_long_after_its_task_keeps_its_hours_on_the_months_of_the_task(
    stage: Scene, offer: tuple[UUID, Costing]
) -> None:
    # Propre à l'US : « au jour courant, la même fonction de calcul donne les mêmes documents »
    # (EP-11, « La contribution d'un projet ») — the workload of an offer on its estimate, whatever
    # the day (#4284). The offer is not marked, and the day read is seventy days after the end of
    # its task: its eight hours stay on the months of the task, none on the month of the day.
    revision_id, costs = offer
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        tasks = tasks_for_indicators(session, project_id, revision_id)
    (task,) = [each for each in tasks if each.label == "Études"]
    months = {f"{each:%Y-%m}" for each in (task.start.day, task.finish.day)}
    day = task.finish.day + timedelta(days=70)
    at = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
    with stage.database.transaction() as session:
        computed = day_contribution(session, project_id=project_id, revision_id=revision_id, at=at)
    (role,) = computed[WORKLOAD]["roles"]
    assert role["resource_role_id"] == str(costs.role)
    held = {each["month"]: Decimal(each["hours"]) for each in role["months"]}
    assert set(held) <= months
    assert f"{day:%Y-%m}" not in held
    assert sum(held.values(), Decimal(0)) == Decimal("8.00")


@pytest.mark.story("US-2680")
def test_the_workload_of_a_marked_offer_is_read_on_the_roles_its_marking_kept(
    stage: Scene, offer: tuple[UUID, Costing]
) -> None:
    # Propre à l'US : le marquage conserve « la charge par rôle de ressource et par mois — sur le
    # devis d'une offre » ; read again after it, the workload of the marked offer is read on the
    # roles its images kept (``estimate_workload``, #4284): the role renamed after the marking keeps
    # its label of then, and its hours, where a revision opened afterwards reads it renamed.
    revision_id, costs = offer
    project_id = UUID(stage.project["project_id"])
    manager = stage.manager.user_id
    mark(stage, revision_id, Act(manager, utc_now()))
    with stage.database.transaction() as session:
        before = offer_workload(session, project_id, revision_id, AT)
    (former,) = [each.label for each in before if each.resource_role_id == costs.role]
    with stage.owner.begin() as connection:
        renamed = update(ResourceRole).where(ResourceRole.id == costs.role)
        connection.execute(renamed.values(label=f"{former} (renommé)"))
    with stage.database.transaction() as session:
        after = offer_workload(session, project_id, revision_id, AT)
        opened = create_revision(
            session, project_id, Act(manager, utc_now()), Viewer(manager, MANAGING)
        ).revision_id
        current = offer_workload(session, project_id, opened, AT)
    assert after == before
    (held,) = [each for each in after if each.resource_role_id == costs.role]
    assert held.label == former
    assert sum((each.hours for each in held.months), Decimal(0)) == Decimal("8.00")
    (read,) = [each for each in current if each.resource_role_id == costs.role]
    assert read.label == f"{former} (renommé)"


@pytest.mark.story("US-2680")
def test_the_budget_names_its_natures_as_its_reference_kept_them_the_remaining_as_it_reads_them(
    fabrics: Portfolio,
) -> None:
    # Propre à l'US : « les totaux par nature de coût du budget de référence, hors lignes de
    # provision, et du reste à engager ». The nature of the material is renamed after the reference
    # of the project kept its images: the budget, read on the reference, names it as the reference
    # kept it; the remaining of the current revision, as it reads it now. Neither label is lost.
    running = fabrics.in_progress
    manager = fabrics.stage.manager.user_id
    with fabrics.stage.database.transaction() as session:
        revision_id = create_revision(
            session, running.project_id, Act(manager, AT), Viewer(manager, MANAGING)
        ).revision_id
        before = portfolio_totals(session, running.project_id, revision_id)
    (material,) = [
        key for key, amount in before.budget_by_cost_type.items() if amount == Decimal("1000.00")
    ]
    former = before.budget_cost_type_labels[material]
    renamed = f"{former} (renommée)"
    with fabrics.stage.owner.begin() as connection:
        connection.execute(update(CostType).where(CostType.id == material).values(label=renamed))
    with fabrics.stage.database.transaction() as session:
        totals = portfolio_totals(session, running.project_id, revision_id)
        document = contributing.cost_structure_document(session, running.project_id, revision_id)
    assert totals.budget_revision_id == running.marked[OFFER][0]
    assert totals.budget_cost_type_labels[material] == former
    assert totals.remaining_cost_type_labels[material] == renamed
    labels = {
        each: {entry["cost_type_id"]: entry["label"] for entry in document[each]}
        for each in ("budget_by_cost_type", "remaining_by_cost_type")
    }
    assert labels["budget_by_cost_type"][str(material)] == former
    assert labels["remaining_by_cost_type"][str(material)] == renamed


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_marking_fails_whole_when_the_computation_of_the_portfolio_raises(
    stage: Scene, offer: tuple[UUID, Costing], monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Le marquage d'une révision échoue entièrement si le calcul de ses indicateurs échoue. » :
    # l'enregistrement du portefeuille s'exécute dans la même transaction, et une exception de son
    # calcul fait échouer le marquage de la même façon — the revision stays current, and nothing it
    # would have kept is written, the indicators of EP-10 kept before it included.
    revision_id, _ = offer

    def failing(session: Session, project_id: UUID, revision: UUID) -> Document:
        del session, project_id, revision
        msg = "the structure of the costs fails"
        raise RuntimeError(msg)

    monkeypatch.setattr(contributing, "cost_structure_document", failing)
    with pytest.raises(RuntimeError, match="the structure of the costs fails"):
        mark(stage, revision_id, Act(stage.manager.user_id, utc_now()))
    with stage.database.transaction() as session:
        revision = session.get(Revision, revision_id)
        assert revision is not None
        assert (revision.status, revision.marked_at) == ("draft", None)
        written = session.scalar(
            select(RevisionIndicator.id).where(RevisionIndicator.revision_id == revision_id)
        )
    assert written is None


@pytest.mark.story("US-2680")
def test_the_loader_of_the_witness_keeps_the_portfolio_by_load_marking(
    stage: Scene, offer: tuple[UUID, Costing]
) -> None:
    # Propre à l'US : « la fusion d'un différentiel (EP-08), qui marque, les conserve de même, et le
    # chargeur du témoin par ``load_marking`` » : the loader marks at the instant it imposes, and
    # the documents of the portfolio are kept at it, as the worker's marking keeps them.
    revision_id, _ = offer
    act = Act(None, datetime(2026, 2, 16, 9, 0, tzinfo=UTC))
    with logging_context(correlation_id="witness"), stage.database.transaction() as session:
        load_marking(session, revision_id, "Offre v1.0", None, act)
    assert instants_of(stage.owner, revision_id) == {(kind, act.at, act.at) for kind in OFFER_KINDS}


# --- The milestones, and the same computation on the current day ---------------------------------


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the marking is made on."""
    return clock_setter(monkeypatch)


@pytest.mark.story("US-2680")
def test_a_review_keeps_its_tracked_milestones_and_the_day_computes_the_same_documents(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # Propre à l'US : « ce que la santé du pilotage constate d'une révision — ses jalons inscrits au
    # suivi, leur date de référence et leur terminaison » ; « au jour courant, la même fonction de
    # calcul donne les mêmes documents » (EP-11, « La contribution d'un projet »). The studies are
    # forecast later than the reference and the delivery is completed: each keeps its date in the
    # reference and its completion. Computed again for the current day on the revision marked, at
    # the instant of its marking, the documents are those its marking kept.
    project = Project(api, stage, clock)
    project.track(STUDIES, TIME_TIME)
    project.track(DELIVERY, TIME_TIME)
    project.date(STUDIES, START + timedelta(days=60))
    project.progress(DELIVERY, "completed", START)
    revision_id = UUID(project.tree.revision["revision_id"])
    clock(START)
    marked_at = marked(stage, project.tree.revision, "Revue 1")
    kept = kept_of(stage.database, revision_id)
    with stage.database.transaction() as session:
        reference = project_facts(session, project.project_id).reference_revision_id
        assert reference is not None
        milestones = kept[MILESTONES]["milestones"]
        lineages = [UUID(each["lineage_id"]) for each in milestones]
        planned = milestone_forecasts(session, project.project_id, lineages, [reference])[reference]
        computed = day_contribution(
            session, project_id=project.project_id, revision_id=revision_id, at=marked_at
        )
    assert [each["label"] for each in milestones] == [STUDIES, DELIVERY]
    for each in milestones:
        assert each["reference_date"] == planned[UUID(each["lineage_id"])].isoformat()
    assert [each["completed_on"] for each in milestones] == [None, START.isoformat()]
    assert set(kept) & set(KEPT_HERE) == set(PROJECT_KINDS)
    assert {kind: computed[kind] for kind in PROJECT_KINDS} == {
        kind: kept[kind] for kind in PROJECT_KINDS
    }
    assert "project" in computed


# --- The key of the contribution of the day ------------------------------------------------------


@dataclass
class Counted:
    """The contribution of the day of the portfolio, which records each project it computes."""

    calls: list[UUID] = field(default_factory=list[UUID])

    def __call__(
        self, session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
    ) -> Mapping[IndicatorKind, Document]:
        self.calls.append(project_id)
        return day_contribution(session, project_id=project_id, revision_id=revision_id, at=at)


class Written(IndicatorsCache):
    """The cache of the indicators, which records the keys it writes."""

    def __init__(self, client: Redis, ttl: int) -> None:
        """Record nothing yet."""
        super().__init__(client, ttl)
        self.written: set[str] = set()

    def write_many(self, documents: Mapping[str, str]) -> None:
        """Record the keys, then write."""
        self.written.update(documents)
        super().write_many(documents)


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[Written]:
    """Give the cache of the indicators beside the queue of the test; the entries it wrote deleted.

    Those alone: another test may share the Redis of the tests.
    """
    opened = Written.of(queue, TTL)
    yield opened
    if opened.written:
        opened.client.delete(*(PREFIX + key for key in opened.written))
    opened.close()


def key_of(fabrics: Portfolio, project_id: UUID, revision_id: UUID) -> str:
    """Give the key of the contribution of a project at ``AT``."""
    with fabrics.stage.database.transaction() as session:
        return contribution_key(session, project_id, revision_id, AT, roles_stamp(session))


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_change_of_a_role_or_of_the_probability_is_not_served_from_the_entry_before(
    fabrics: Portfolio, cache: IndicatorsCache
) -> None:
    # Propre à l'US : « l'empreinte sous laquelle le cache garde la contribution d'un projet couvre
    # ce que la contribution lit : le nœud courant d'un rôle et la probabilité de gain d'une offre ;
    # un changement de l'une de ces valeurs n'est pas servi d'après l'entrée ancienne » (#4158). A
    # role written — deactivated here — leaves the fingerprint of the day as it was and changes the
    # key of the contribution; the probability of the offer changes it too. Each time, the next
    # reading computes the offer again.
    offer = fabrics.offer
    revision_id = offer.marked[OFFER][0]
    revisions = {offer.project_id: revision_id}
    counted = Counted()

    def read() -> dict[IndicatorKind, Document]:
        with fabrics.stage.database.transaction() as session:
            found = day_documents_of(
                session, revisions, AT, Contributing(counted, DAY_KINDS), cache
            )
        return found[offer.project_id]

    first = read()
    assert set(first) == {"estimate", *OFFER_KINDS}
    # Served from the cache, the contribution is the one computed, to its types.
    assert read() == first
    assert counted.calls == [offer.project_id]
    before = key_of(fabrics, offer.project_id, revision_id)
    with fabrics.stage.database.transaction() as session:
        role = fabrics.costs.role
        counter = read_role(session, role, may_change=False).lock_version
        act = Act(fabrics.stage.manager.user_id, AT)
        set_role_activation(session, role, is_active=False, lock_version=counter, act=act)
    after_role = key_of(fabrics, offer.project_id, revision_id)
    assert after_role != before
    assert after_role.split(":portfolio:")[0] == before.split(":portfolio:")[0]
    read()
    assert counted.calls == [offer.project_id] * 2
    manager = fabrics.stage.manager.user_id
    with fabrics.stage.database.transaction() as session:
        change = ProjectChange(
            {"win_probability": Decimal("0.60")}, stored_lock_version(session, offer.project_id)
        )
        update_project(
            session, offer.project_id, change, Act(manager, AT), Viewer(manager, MANAGING)
        )
    assert key_of(fabrics, offer.project_id, revision_id) != after_role
    read()
    assert counted.calls == [offer.project_id] * 3


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_change_of_the_hours_of_the_calendar_of_a_role_changes_the_key_of_the_contribution(
    fabrics: Portfolio,
) -> None:
    # « WF-DAT-0130-A » : the workload is spread over the hours of the calendar of each role. The
    # calendar of a role of its own, not the default — whose change redates the structures —, gets
    # an hour less on Mondays: no role is written, the fingerprint of the day stays as it was, and
    # the key of the contribution changes, by the stamp of the calendars alone (#4284): the number,
    # the counters and the last write of the roles stay as they were, the counters of the calendars
    # advance, their number unchanged.
    role = add_role(fabrics.stage.database, "CAL", (8, 8, 8, 8, 8, 0, 0))
    offer = fabrics.offer
    revision_id = offer.marked[OFFER][0]
    before = key_of(fabrics, offer.project_id, revision_id)
    with fabrics.stage.database.transaction() as session:
        stamped = roles_stamp(session)
    with fabrics.stage.database.transaction() as session:
        calendar = read_calendar(session, read_role(session, role, may_change=False).calendar_id)
        eight, nought = Decimal(8), Decimal(0)
        hours = WeeklyHours(Decimal(7), eight, eight, eight, eight, nought, nought)
        update_calendar(
            session,
            calendar.calendar_id,
            CalendarContent(calendar.label, hours),
            calendar.lock_version,
            Act(fabrics.stage.manager.user_id, AT),
        )
    after = key_of(fabrics, offer.project_id, revision_id)
    assert after != before
    assert after.split(":portfolio:")[0] == before.split(":portfolio:")[0]
    with fabrics.stage.database.transaction() as session:
        restamped = roles_stamp(session)
    assert (restamped.count, restamped.versions, restamped.updated_at) == (
        stamped.count,
        stamped.versions,
        stamped.updated_at,
    )
    assert restamped.calendar_count == stamped.calendar_count
    assert restamped.calendar_versions == stamped.calendar_versions + 1


# --- The PostgreSQL of the tests -----------------------------------------------------------------


@pytest.mark.story("US-2680")
def test_the_postgresql_of_the_tests_holds_the_locks_of_the_fabrics(owner: Engine) -> None:
    # Propre à l'US : « le PostgreSQL des tests monte ``max_locks_per_transaction`` » (#4051): the
    # partitions of the fabrics, dropped project after project by the fixture ``database``, and two
    # runs that share the server, no longer exhaust the shared table of the locks.
    with owner.connect() as connection:
        held = connection.scalar(text("SHOW max_locks_per_transaction"))
    assert int(str(held)) >= 256


@pytest.mark.story("US-2680")
def test_the_partitions_are_dropped_project_after_project_a_transaction_each(
    owner: Engine, database: Database
) -> None:
    # Propre à l'US : « la fixture ``database`` supprime les partitions projet par projet, une
    # transaction chacun » (#4051). Each project is dropped by a transaction of its own: none drops
    # the partitions of two projects.
    del database
    projects = [uuid4(), uuid4()]
    with owner.begin() as connection:
        for project_id in projects:
            connection.execute(insert_project(id=project_id))
            connection.execute(select(func.create_project_partitions(project_id)))
    dropped: list[set[UUID]] = []

    def began(*call: Any) -> None:
        del call
        dropped.append(set())

    def seen(*call: Any) -> None:
        statement = str(call[2])
        for project_id in projects:
            if statement.startswith("DROP TABLE") and project_id.hex in statement:
                dropped[-1].add(project_id)

    event.listen(owner, "begin", began)
    event.listen(owner, "before_cursor_execute", seen)
    try:
        drop_every_partition(owner)
    finally:
        event.remove(owner, "begin", began)
        event.remove(owner, "before_cursor_execute", seen)
    assert [each for each in dropped if each] == [{project} for project in sorted(projects)]
    with owner.connect() as connection:
        assert not set(projects) & set(partitioned_projects(connection))
