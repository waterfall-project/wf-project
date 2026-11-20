# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contribution of a project to the portfolio, computed once for both dates (US-2680/L2).

One computation gives the documents of the portfolio of a revision, at the marking and on the
current day (EP-11, "La contribution d'un projet"): ``portfolio_documents``. The marking keeps what
it gives (``store_contribution``, in the interface); the day adds the document the list and the
value read — ``project`` or ``estimate``, EP-10's — and keeps the whole in the cache of the
indicators (``day_contribution``). Their forms are those of the interface
(``core/portfolio/interface/contribution.py``), which the views read.

Which kinds a revision gives follows the state of its project: a project In progress or Completed
gives the workload, the structure of the costs and the milestones; an offer the workload and the
structure of the costs on its estimate, and its curves — not the milestones, which ask for a
reference. A marking keeps the kinds of the state of its project then: a project In progress, or an
offer; a project in another state keeps none. The risks join with US-2680/L3.

Each part reads through the interfaces of the modules, never their tables: the workload of the
estimate (``workload``, EP-07, on a remaining; ``offer_workload`` on the estimate of an offer), its
totals (``portfolio_totals``), the tracked milestones of the planning and the curves of an offer of
the indicators (``offer_curves``). Nothing is weighted: the views weigh an offer by its probability
(EP-11, "La contribution d'un projet").
"""

from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.costs.interface import PROJECT
from waterfall.core.estimate import interface as estimate
from waterfall.core.estimate.interface import (
    IndicatorsAsked,
    WorkloadAsked,
    WorkloadBasis,
    estimate_indicators,
    offer_workload,
    portfolio_totals,
)
from waterfall.core.indicators.interface import (
    Contributing,
    day_indicators,
    day_reading_of,
    estimate_document,
    offer_curves,
)
from waterfall.core.planning.interface import (
    milestone_forecasts,
    tasks_for_indicators,
    tracked_milestones,
)
from waterfall.core.portfolio.states import IN_PROGRESS, PRICING
from waterfall.core.projects.interface import Viewer, project_facts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import date, datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import RoleLoad
    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.core.projects.interface import ProjectFacts

# Who reads a marked revision for its workload: no account, no permission (the commands of the
# revision are not read).
NOBODY = Viewer(UUID(int=0), ())
COMPLETED_TASK = "completed"

WORKLOAD: IndicatorKind = "portfolio_workload"
COST_STRUCTURE: IndicatorKind = "portfolio_cost_structure"
MILESTONES: IndicatorKind = "portfolio_milestones"
OFFER_CURVES: IndicatorKind = "portfolio_offer_curves"

# The kinds every entry of the day answers, a document or none (``day_documents_of``, #4193): those
# of EP-10 the list and the value read, and those of the portfolio.
DAY_KINDS: tuple[IndicatorKind, ...] = (
    "project",
    "estimate",
    WORKLOAD,
    COST_STRUCTURE,
    MILESTONES,
    OFFER_CURVES,
)

type Documents = Mapping[IndicatorKind, Document]


def _hours(value: Decimal) -> str:
    """Write hours or an amount as the contract does, without an exponent."""
    return format(value, "f")


def workload_document(
    session: Session, facts: ProjectFacts, project_id: UUID, revision_id: UUID, at: datetime
) -> Document:
    """Give the hours of each role by month of a revision: its remaining, or an offer's estimate.

    A project that is not an offer on its remaining to commit (``getProjectWorkload``): that of the
    current revision from the day of ``at``, that of a marked one from the day of its marking. An
    offer on its estimate, every line whole over its task, whatever the day (``offer_workload``;
    EP-11, "Tables et migrations"). Only the roles loaded, in the order of the workload, each with
    its months loaded in order.
    """
    roles: Sequence[RoleLoad]
    if facts.state == PRICING:
        roles = offer_workload(session, project_id, revision_id, at)
    else:
        current = revision_id == facts.current_revision_id
        basis = WorkloadBasis.CURRENT_REMAINING if current else WorkloadBasis.MARKED_REMAINING
        asked = WorkloadAsked(basis, None if current else revision_id, None, at, NOBODY)
        # Read on the interface itself: ``workload`` names a file of it too.
        roles = estimate.workload(session, project_id, asked).roles
    return {
        "roles": [
            {
                "resource_role_id": str(role.resource_role_id),
                "months": [
                    {"month": each.month, "hours": _hours(each.hours)} for each in role.months
                ],
            }
            for role in roles
            if role.months
        ]
    }


def _amounts(amounts: Mapping[UUID, Decimal], key: str) -> list[dict[str, str]]:
    """Write amounts by key, in the order of their identifiers."""
    return [{key: str(each), "amount": _hours(amounts[each])} for each in sorted(amounts)]


def cost_structure_document(session: Session, project_id: UUID, revision_id: UUID) -> Document:
    """Give the totals by cost type of the budget and of the remaining, and their labour by role."""
    totals = portfolio_totals(session, project_id, revision_id)

    def by_type(
        amounts: Mapping[UUID, Decimal], labels: Mapping[UUID, str]
    ) -> list[dict[str, str]]:
        return [
            {"cost_type_id": str(each), "label": labels[each], "amount": _hours(amounts[each])}
            for each in sorted(amounts)
        ]

    return {
        "budget_revision_id": str(totals.budget_revision_id),
        "budget_by_cost_type": by_type(totals.budget_by_cost_type, totals.budget_cost_type_labels),
        "remaining_by_cost_type": by_type(
            totals.remaining_by_cost_type, totals.remaining_cost_type_labels
        ),
        "budget_labour_by_role": _amounts(totals.budget_labour_by_role, "resource_role_id"),
        "remaining_labour_by_role": _amounts(totals.remaining_labour_by_role, "resource_role_id"),
    }


def milestones_document(
    session: Session, facts: ProjectFacts, project_id: UUID, revision_id: UUID
) -> Document:
    """Give the milestones of a revision inscribed in the time/time tracking, in the plan's order.

    Each with its lineage, its label, its date in the reference — none when the reference does
    not hold it — and the day it was completed, none while it is not (WF-PTF-0110, WF-IND-0090).
    """
    tracked = set(tracked_milestones(session, project_id))
    tasks = [
        each
        for each in tasks_for_indicators(session, project_id, revision_id)
        if each.is_milestone and each.lineage_id in tracked
    ]
    reference = facts.reference_revision_id
    dates: Mapping[UUID, date] = {}
    if reference is not None:
        lineages = [each.lineage_id for each in tasks]
        dates = milestone_forecasts(session, project_id, lineages, [reference]).get(reference, {})
    milestones: list[dict[str, str | None]] = []
    for task in tasks:
        planned = dates.get(task.lineage_id)
        done = task.completed_on if task.progress == COMPLETED_TASK else None
        milestones.append(
            {
                "lineage_id": str(task.lineage_id),
                "label": task.label,
                "reference_date": None if planned is None else planned.isoformat(),
                "completed_on": None if done is None else done.isoformat(),
            }
        )
    return {"milestones": milestones}


def portfolio_documents(
    session: Session, project_id: UUID, revision_id: UUID, at: datetime, *, marking: bool
) -> dict[IndicatorKind, Document]:
    """Give the documents of the portfolio of a revision of a project, by kind, at ``at``.

    ``marking`` is the revision being marked at the instant ``at`` of its act: its state then
    decides — In progress, or an offer —, and the curves of an offer bear the context a marking
    keeps. On the current day, a project that is not an offer gives what a project In progress
    gives. Nothing is caught: a computation that raises fails the marking whole.
    """
    facts = project_facts(session, project_id)
    if facts.state == PRICING:
        return {
            WORKLOAD: workload_document(session, facts, project_id, revision_id, at),
            COST_STRUCTURE: cost_structure_document(session, project_id, revision_id),
            OFFER_CURVES: offer_curves(session, revision_id, at, marking=marking),
        }
    if marking and facts.state != IN_PROGRESS:
        return {}
    return {
        WORKLOAD: workload_document(session, facts, project_id, revision_id, at),
        COST_STRUCTURE: cost_structure_document(session, project_id, revision_id),
        MILESTONES: milestones_document(session, facts, project_id, revision_id),
    }


def day_contribution(
    session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
) -> Documents:
    """Give the documents of the day a project contributes, every kind its state calls for.

    Its estimate if an offer, else its own indicators — the same documents as the readings of the
    project give (``getEstimateIndicators``, ``getProjectIndicators``), on the revision of the day,
    zones null: they are classified when the list is read, on the thresholds of that day
    (WF-REF-0170) —; then the documents of the portfolio, as a marking would keep them on that
    revision (``portfolio_documents``). One computation for every view, written whole in the cache:
    an entry never holds some of the kinds alone (#4193).
    """
    found: dict[IndicatorKind, Document]
    if project_facts(session, project_id).state == PRICING:
        asked = IndicatorsAsked(revision_id, str(PROJECT), at)
        found = {"estimate": estimate_document(estimate_indicators(session, project_id, asked))}
    else:
        reading = day_reading_of(session, project_id, revision_id, at)
        found = {"project": day_indicators(session, reading, (PROJECT,), None)[PROJECT]}
    found.update(portfolio_documents(session, project_id, revision_id, at, marking=False))
    return found


# The contribution of the day, with the kinds every entry of the cache answers.
DAY_CONTRIBUTION = Contributing(day_contribution, DAY_KINDS)
