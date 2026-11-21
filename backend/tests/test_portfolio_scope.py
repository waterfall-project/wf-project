# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope of the portfolio, resolved on the database (``resolve_scope``, US-2670/L3).

The states asked and the state of a project at a date by its transitions; the period, the default
one included, and its refusal; the node and its label; the revision each project contributes by and
its weight; the offers closed in a period, its bounds included; the projects a reader opens. On the
four projects of the fabrics (``portfolio_support``), read at instants of their chronology. The
criteria that ask for a view, read on the service, are closed by the views (US-2670/L4).

Each test that writes the fabrics reads them several ways: every test drops the partitions of its
projects at its end, and a dozen doing so at once, one per process, exhaust the locks of the
server of the tests (``max_locks_per_transaction``).
"""

import inspect
from annotationlib import Format
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from portfolio_support import (
    COMPLETED_ON,
    LOST_ON,
    OFFER,
    OFFER_PROBABILITY,
    READ_ON,
    REVIEW,
    Portfolio,
    at,
    portfolio,
)
from project_rows import REPLICA
from projects_support import MANAGING, Scene, contribute, create
from projects_support import scene as make_scene
from sqlalchemy import event, select, update

from waterfall.core.portfolio import interface
from waterfall.core.portfolio.interface import (
    PeriodRule,
    PortfolioAsked,
    ResolvedScope,
    period_instants,
    resolve_scope,
)
from waterfall.core.projects.interface import (
    ClosedOffer,
    ProjectChange,
    Viewer,
    offers_closed_between,
    openable,
    projects_in_states_on,
    stored_lock_version,
    update_project,
)
from waterfall.core.projects.tables import STATES, Project, ProjectStateTransition
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole
from waterfall.core.revisions.interface import (
    RetainedRevisions,
    create_revision,
    last_marked_at_instant,
)
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.installation import TIME_ZONE
from waterfall.platform.logs import logging_context
from waterfall.platform.permissions import ALL_PROJECTS_READ

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.projects.interface import ProjectState
    from waterfall.platform.database import Database

# The instant a view is read at: its current day, 19 November 2026, after the whole chronology.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
# What a view of the value counts: In progress, Pricing, and Completed in the period.
VALUE: frozenset[ProjectState] = frozenset({"in_progress", "pricing", "completed"})
EVERY: tuple[ProjectState, ...] = ("in_progress", "pricing", "completed", "lost", "created")


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def _resolved(
    database: Database,
    asked: PortfolioAsked,
    *,
    counted: frozenset[ProjectState] = VALUE,
    period: bool = True,
) -> ResolvedScope:
    with database.transaction() as session:
        return resolve_scope(
            session, asked, NOW, counted=counted, period=PeriodRule() if period else None
        )


def _refused(database: Database, asked: PortfolioAsked) -> list[tuple[str, str, object]]:
    with pytest.raises(UnprocessableError) as refusal:
        _resolved(database, asked)
    assert refusal.value.code == "VALIDATION_FAILED"
    return [(each.pointer, each.code, dict(each.params)) for each in refusal.value.fields]


def _project_act(fabrics: Portfolio, instant: datetime) -> tuple[Act, Viewer]:
    manager = fabrics.stage.manager.user_id
    return Act(manager, instant), Viewer(manager, MANAGING)


def _probability_changed(fabrics: Portfolio, project_id: UUID, probability: str) -> None:
    """Change the probability of winning of an offer after its marking, on 10 June."""
    act, viewer = _project_act(fabrics, at(6, 10))
    with logging_context(correlation_id="probability"), fabrics.stage.database.transaction() as s:
        change = ProjectChange(
            {"win_probability": Decimal(probability)}, stored_lock_version(s, project_id)
        )
        update_project(s, project_id, change, act, viewer)


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_scope_gives_the_states_the_date_the_period_the_node_and_the_projects_retained(
    fabrics: Portfolio,
) -> None:
    # « Chaque vue rend le périmètre retenu (PortfolioScope) — les états demandés ou, sans eux, les
    # projets en cours ; la date de calcul, le jour courant du fuseau de l'installation sans
    # as_of ; la période, celle par défaut comprise ; le nœud et son libellé ; le nombre de
    # projets retenus ; un état que la vue ne compte pas est sans effet, jamais refusé. »
    database = fabrics.stage.database
    with database.transaction() as session:
        node_id, label = session.execute(
            select(OrgNode.id, OrgNode.label)
            .join(ResourceRole, ResourceRole.org_node_id == OrgNode.id)
            .where(ResourceRole.id == fabrics.costs.role)
        ).one()
    resolved = _resolved(database, PortfolioAsked(org_node_id=node_id))
    scope = resolved.scope
    assert (scope.states, scope.as_of) == (("in_progress",), date(2026, 11, 19))
    assert (scope.period_from, scope.period_to) == (date(2025, 11, 20), date(2026, 11, 19))
    assert (scope.org_node_id, scope.org_node_label) == (node_id, label)
    assert resolved.on_current_day
    assert set(resolved.projects) == {fabrics.in_progress.project_id}
    assert scope.project_count == 1
    # Read on 3 June, every state asked: the completion of 15 April is in the default period, the
    # loss and Created are not counted, and stay in the scope.
    resolved = _resolved(database, PortfolioAsked(states=EVERY, as_of=READ_ON))
    assert (resolved.scope.states, resolved.scope.as_of) == (EVERY, READ_ON)
    assert (resolved.scope.org_node_id, resolved.scope.org_node_label) == (None, None)
    assert not resolved.on_current_day
    assert {key: each.state for key, each in resolved.projects.items()} == {
        fabrics.in_progress.project_id: "in_progress",
        fabrics.offer.project_id: "pricing",
        fabrics.completed.project_id: "completed",
    }
    assert resolved.scope.project_count == len(resolved.projects)


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_state_at_a_date_is_read_from_the_transitions_and_a_completion_from_the_period(
    fabrics: Portfolio,
) -> None:
    # « L'état d'un projet à une date est celui de sa dernière transition datée de ce jour ou
    # d'avant (WF-CYC-0130) » : completed on 15 April, it is In progress on the 14th.
    database = fabrics.stage.database
    completed = fabrics.completed.project_id
    states: tuple[ProjectState, ...] = ("in_progress", "completed")
    before = _resolved(database, PortfolioAsked(states=states, as_of=date(2026, 4, 14)))
    on = _resolved(database, PortfolioAsked(states=states, as_of=COMPLETED_ON.date()))
    assert before.projects[completed].state == "in_progress"
    assert on.projects[completed].state == "completed"
    # A project Completed counts when completed in the period, bounds included (G-05).
    asked = PortfolioAsked(states=("completed",), as_of=READ_ON)
    periods = {
        (date(2026, 4, 15), None): True,
        (date(2026, 4, 16), None): False,
        (date(2026, 4, 1), date(2026, 4, 15)): True,
        (date(2026, 4, 1), date(2026, 4, 14)): False,
    }
    found = {
        bounds: completed
        in _resolved(database, replace(asked, period_from=bounds[0], period_to=bounds[1])).projects
        for bounds in periods
    }
    assert found == periods
    # Without a period, the view decides by what it counts (#4020, to decide): ``from`` and ``to``
    # are not read, an inverted pair is not refused, and the scope gives no period.
    unbounded = PortfolioAsked(
        states=states, period_from=date(2026, 5, 1), period_to=date(2026, 1, 1)
    )
    counting = _resolved(database, unbounded, period=False)
    not_counting = _resolved(database, unbounded, counted=frozenset({"in_progress"}), period=False)
    not_asked = _resolved(database, replace(unbounded, states=("in_progress",)), period=False)
    assert counting.projects[completed].state == "completed"
    assert (counting.scope.period_from, counting.scope.period_to) == (None, None)
    assert completed not in not_counting.projects
    assert completed not in not_asked.projects


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_default_period_starts_the_day_after_the_date_minus_twelve_months(
    database: Database,
) -> None:
    # ``PortfolioTo``: 4 June 2025 for 3 June 2026, 1 March 2027 for 29 February 2028.
    for as_of, start in ((READ_ON, date(2025, 6, 4)), (date(2028, 2, 29), date(2027, 3, 1))):
        scope = _resolved(database, PortfolioAsked(as_of=as_of)).scope
        assert (scope.period_from, scope.period_to) == (start, as_of)


@pytest.mark.requirement("WF-PTF-0010-A")
def test_a_period_inverted_or_starting_after_its_default_end_is_refused(
    database: Database,
) -> None:
    # « Une période inversée, ou qui commence après sa fin par défaut, est refusée par 422
    # (PortfolioPeriodRefused), par une seule règle pour les six vues qui prennent une période. »
    inverted = PortfolioAsked(period_from=date(2026, 3, 31), period_to=date(2026, 1, 1))
    assert _refused(database, inverted) == [
        ("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2026-03-31"})
    ]
    after_end = PortfolioAsked(period_from=date(2026, 9, 1), as_of=READ_ON)
    assert _refused(database, after_end) == [
        ("/query/from", "VALUE_OUT_OF_RANGE", {"maximum": "2026-06-03"})
    ]
    before_start = PortfolioAsked(period_to=date(2025, 6, 3), as_of=READ_ON)
    assert _refused(database, before_start) == [
        ("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2025-06-04"})
    ]
    # A period of one day, or one bound completed by the default other, is not refused.
    single = _resolved(database, PortfolioAsked(period_from=READ_ON, period_to=READ_ON))
    assert (single.scope.period_from, single.scope.period_to) == (READ_ON, READ_ON)
    first_day = _resolved(database, PortfolioAsked(period_to=date(2025, 6, 4), as_of=READ_ON))
    assert (first_day.scope.period_from, first_day.scope.period_to) == (
        date(2025, 6, 4),
        date(2025, 6, 4),
    )


@pytest.mark.requirement("WF-PTF-0010-A")
def test_an_unknown_node_is_refused_with_the_period_in_one_refusal(database: Database) -> None:
    # « Un nœud inconnu est refusé par 422 sur /query/org_node_id. »
    asked = PortfolioAsked(period_from=date(2027, 1, 1), org_node_id=uuid4())
    assert _refused(database, asked) == [
        ("/query/from", "VALUE_OUT_OF_RANGE", {"maximum": "2026-11-19"}),
        ("/query/org_node_id", "UNKNOWN_ORG_NODE", {}),
    ]


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_revision_retained_is_the_current_one_on_the_current_day_and_the_last_marked_before(
    fabrics: Portfolio,
) -> None:
    # « Au jour courant, chaque projet contribue par ses indicateurs du jour ; à une date passée,
    # par les documents que sa dernière révision marquée à cette date a conservés ; un projet sans
    # révision marquée à cette date est retenu selon son état et ne contribue à aucune somme. »
    database = fabrics.stage.database
    running = fabrics.in_progress.project_id
    offer, review = (fabrics.in_progress.marked[name][0] for name in (OFFER, REVIEW))
    # Without a current revision, the review just marked; at a past date, the last marked by the
    # end of that day — the review is marked on 2 March at nine, universal time.
    assert _resolved(database, PortfolioAsked()).projects[running].revision_id == review
    first = PortfolioAsked(as_of=date(2026, 3, 1))
    second = replace(first, as_of=date(2026, 3, 2))
    assert _resolved(database, first).projects[running].revision_id == offer
    assert _resolved(database, second).projects[running].revision_id == review
    # The offer, priced from 2 February, is marked on 16 February: retained on the 10th, by
    # nothing.
    pricing = PortfolioAsked(states=("pricing",), as_of=date(2026, 2, 10))
    unmarked = _resolved(database, pricing).projects[fabrics.offer.project_id]
    assert (unmarked.state, unmarked.revision_id, unmarked.weight) == ("pricing", None, None)
    # A revision opened: the current day reads it, a past date still the last marked by then.
    act, viewer = _project_act(fabrics, at(6, 10))
    with logging_context(correlation_id="opening"), database.transaction() as session:
        opened = create_revision(session, running, act, viewer).revision_id
    retained = _resolved(database, PortfolioAsked()).projects[running]
    assert (retained.revision_id, retained.weight) == (opened, Decimal(1))
    past = _resolved(database, PortfolioAsked(as_of=READ_ON)).projects[running]
    assert past.revision_id == review
    # An ``as_of`` equal to the current day is a date asked: read by the markings, not by the
    # revision in progress.
    today = _resolved(database, PortfolioAsked(as_of=NOW.date()))
    assert today.projects[running].revision_id == review
    assert not today.on_current_day
    assert _resolved(database, PortfolioAsked()).on_current_day
    # The end of the day is that of the time zone of the installation: at Honolulu, ten hours
    # behind, the marking of the review falls on 1 March.
    TIME_ZONE.read_from(lambda: "Pacific/Honolulu")
    assert _resolved(database, first).projects[running].revision_id == review


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_weight_of_an_offer_at_a_past_date_is_the_probability_its_marking_kept(
    fabrics: Portfolio, owner: Engine
) -> None:
    # « La probabilité de gain étant celle que ce marquage a gardée (EP-07) » (#4025): the offer
    # marked at 40 % is now at 70 %; read on 3 June it weighs 40 %, on the current day 70 %.
    database = fabrics.stage.database
    offer = fabrics.offer.project_id
    running = fabrics.in_progress.project_id
    _probability_changed(fabrics, offer, "0.70")
    asked = PortfolioAsked(states=("in_progress", "pricing"))
    past = _resolved(database, replace(asked, as_of=READ_ON)).projects
    today = _resolved(database, asked).projects
    assert past[offer].revision_id == fabrics.offer.marked[OFFER][0]
    assert past[offer].weight == OFFER_PROBABILITY
    assert today[offer].weight == Decimal("0.70")
    assert past[running].weight == Decimal(1)
    # Read with ``as_of`` the current day, the offer weighs the probability its marking kept.
    on_the_day = _resolved(database, replace(asked, as_of=NOW.date())).projects
    assert on_the_day[offer].weight == OFFER_PROBABILITY
    # A marking before EP-07 kept no probability: the offer weighs nothing known, a project In
    # progress one.
    with owner.begin() as connection:
        # A marked revision is immutable: the trigger that says so is set aside, as a superuser.
        connection.execute(REPLICA)
        connection.execute(
            update(Revision)
            .where(Revision.project_id.in_([offer, running]), Revision.status == "marked")
            .values(win_probability=None)
        )
    unknown = _resolved(database, replace(asked, as_of=READ_ON)).projects
    assert (unknown[offer].state, unknown[offer].revision_id, unknown[offer].weight) == (
        "pricing",
        fabrics.offer.marked[OFFER][0],
        None,
    )
    assert unknown[running].weight == Decimal(1)
    # The revisions of every project are read together, each asked with its entry.
    ids = [*(each.project_id for each in fabrics.projects), uuid4()]
    with database.transaction() as session:
        kept = last_marked_at_instant(session, ids, at(2, 17))
    assert set(kept) == set(ids)
    assert kept[fabrics.lost.project_id].last_marked_id == fabrics.lost.marked[OFFER][0]
    assert kept[fabrics.lost.project_id].win_probability == Decimal("0.25")
    assert kept[running].last_marked_id == fabrics.in_progress.marked[OFFER][0]
    assert kept[ids[-1]] == RetainedRevisions(None, None, None, None)


@pytest.mark.requirement("WF-CYC-0130-A")
def test_an_offer_lost_on_15_march_is_among_the_offers_closed_in_march_and_no_other_month(
    fabrics: Portfolio,
) -> None:
    # « Un projet passé à Perdu le 15 mars compte parmi les offres closes de mars et d'aucun autre
    # mois. » A statistic of a period retains a transition by its date, bounds included.
    database = fabrics.stage.database
    lost = ClosedOffer(fabrics.lost.project_id, "lost", LOST_ON)

    def closed(start: date, end: date) -> list[ClosedOffer]:
        asked = PortfolioAsked(period_from=start, period_to=end, as_of=READ_ON)
        instants = period_instants(_resolved(database, asked).scope)
        assert instants is not None
        with database.transaction() as session:
            return offers_closed_between(session, *instants)

    assert closed(date(2026, 3, 1), date(2026, 3, 31)) == [lost]
    assert closed(date(2026, 3, 15), date(2026, 3, 15)) == [lost]
    assert lost not in closed(date(2026, 2, 1), date(2026, 2, 28))
    assert lost not in closed(date(2026, 4, 1), date(2026, 4, 30))
    assert lost not in closed(date(2026, 3, 16), date(2026, 3, 31))
    assert lost not in closed(date(2026, 3, 1), date(2026, 3, 14))
    # The offers designated on 19 January left Pricing too, won: January holds them.
    january = closed(date(2026, 1, 1), date(2026, 1, 31))
    assert {(each.project_id, each.to_state) for each in january} == {
        (fabrics.in_progress.project_id, "in_progress"),
        (fabrics.completed.project_id, "in_progress"),
    }


@pytest.mark.requirement("WF-PTF-0030-A")
def test_a_reader_opens_the_projects_it_contributes_to_or_all_with_all_projects_read(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # « Un utilisateur habilité au portefeuille sans « consulter tous les projets », contributeur
    # d'un seul projet du périmètre, voit les totaux de tous et n'ouvre que le sien » : can_open.
    stage = make_scene(api, owner, database, realm)
    own = UUID(stage.project["project_id"])
    other = UUID(create(api, stage.manager)["project_id"])
    ids = [own, other]
    contributor = Viewer(stage.participant.user_id, MANAGING)
    outsider = Viewer(stage.outsider.user_id, MANAGING)
    reader = Viewer(stage.reader.user_id, {ALL_PROJECTS_READ})
    with database.transaction() as session:
        assert openable(session, ids, contributor) == {own}
        assert openable(session, ids, outsider) == frozenset()
        assert openable(session, ids, reader) == frozenset(ids)
        assert openable(session, [], reader) == frozenset()
    contribute(database, str(other), stage.outsider, "project_manager")
    with database.transaction() as session:
        assert openable(session, ids, outsider) == {other}


def _statements(session: Session, read: Callable[[], object]) -> int:
    """Give the number of statements a reading sends to the database."""
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", heard)
    try:
        read()
    finally:
        event.remove(engine, "before_cursor_execute", heard)
    return len(sent)


@pytest.mark.requirement("WF-PTF-0010-A")
def test_each_reading_of_several_projects_is_one_statement_whatever_their_number(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « chaque lecture groupée en une requête » (EP-11, "La contribution d'un projet"), under the
    # scope of WF-PTF-0010-A: the count does not grow with the projects, no reading one by one.
    stage = fabrics.stage
    contributor = Viewer(stage.participant.user_id, MANAGING)
    reader = Viewer(stage.reader.user_id, {ALL_PROJECTS_READ})
    ids = [each.project_id for each in fabrics.projects]

    def counted(session: Session, project_ids: list[UUID]) -> dict[str, int]:
        return {
            "states": _statements(
                session, lambda: projects_in_states_on(session, list(STATES), at(6, 1))
            ),
            "now": _statements(session, lambda: projects_in_states_on(session, list(STATES), None)),
            "marked": _statements(
                session, lambda: last_marked_at_instant(session, project_ids, at(6, 1))
            ),
            "closed": _statements(
                session, lambda: offers_closed_between(session, at(1, 1), at(7, 1))
            ),
            "openable": _statements(session, lambda: openable(session, project_ids, contributor)),
            "all": _statements(session, lambda: openable(session, project_ids, reader)),
            "none": _statements(session, lambda: openable(session, [], contributor)),
        }

    with stage.database.transaction() as session:
        four = counted(session, ids)
    fifth = UUID(create(api, stage.manager)["project_id"])
    with stage.database.transaction() as session:
        five = counted(session, [*ids, fifth])
    expected = {"states": 1, "now": 1, "marked": 1, "closed": 1, "openable": 1, "all": 0, "none": 0}
    assert four == expected
    assert five == expected


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_state_at_an_instant_is_that_of_the_last_transition_ranked_by_the_state_reached(
    fabrics: Portfolio,
) -> None:
    # « L'état d'un projet à une date est celui de sa dernière transition datée de ce jour ou
    # d'avant (WF-CYC-0130) ». Read now, it is the state the project stores; before its creation
    # a project has none; two transitions of one instant — its creation and its first revision —
    # are ranked by the state reached.
    offer = fabrics.offer.project_id
    with fabrics.stage.database.transaction() as session:
        every = projects_in_states_on(session, list(STATES), None)
        stored = {row.id: row.state for row in session.execute(select(Project.id, Project.state))}
        assert {key: each.state for key, each in every.items()} == stored
        assert {each.project_id for each in fabrics.projects} <= set(every)
        assert projects_in_states_on(session, list(STATES), at(1, 1)) == {}
        instants = list(
            session.scalars(
                select(ProjectStateTransition.occurred_at).where(
                    ProjectStateTransition.project_id == offer
                )
            )
        )
        assert len(instants) > len(set(instants))
        both = projects_in_states_on(session, ["created", "pricing"], at(2, 3))
        assert both[offer].state == "pricing"
        assert offer not in projects_in_states_on(session, ["created"], at(2, 3))


@pytest.mark.story("US-2700")
@pytest.mark.parametrize(
    "view",
    [
        "read_portfolio_projects",
        "read_portfolio_value",
        "read_portfolio_workload",
        "read_portfolio_performance",
        "read_portfolio_cost_structure",
        "read_portfolio_risks",
        "read_portfolio_cost_curve",
        "read_pilot_health",
    ],
)
def test_every_view_of_the_portfolio_is_read_by_a_portfolio_reading_and_by_no_loose_instant(
    view: str,
) -> None:
    # Décision de l'auteur du 2026-11-19 (#4194), portée par US-2700 : toute vue lit par
    # ``PortfolioReading(at, cache)``, l'instant et le cache passés ensemble, ni un ``at`` ni un
    # ``cache`` à part.
    # The annotations are read as text: those of the views name their types under ``TYPE_CHECKING``.
    signature = inspect.signature(getattr(interface, view), annotation_format=Format.STRING)
    parameters = signature.parameters
    assert "reading" in parameters
    assert parameters["reading"].annotation == "PortfolioReading"
    assert not {"at", "cache"} & set(parameters)
