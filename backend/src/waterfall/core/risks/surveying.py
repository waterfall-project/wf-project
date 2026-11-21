# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks as the portfolio reads them, private to the module (EP-11, US-2680/L3).

Three readings, offered by ``interface/portfolio.py``:

- the risks of a revision (``survey``), each read as the register reads it (``reading.risk_view``),
  so that the portfolio and the register never disagree on a column: its probability, its
  severity, its provision — identified, the severity weighted by the probability, to the cent;
  occurred or dismissed, the share it held in the reference revision (WF-RIS-0040, H-03) —, its
  state, and for an occurred one its cost at occurrence and the re-estimated amount of the lines
  that came from it (WF-RIS-0050); with the base of the project the matrix relates a severity to
  (WF-REF-0160), from which the portfolio classes each risk at the reading, on the bounds of that
  day (EP-11, "Ce que le cadrage décide");
- the outcomes of a period (``outcomes``): each review that moved a risk to occurred or to
  dismissed, by its day — the occurrence writes one too —, with the provision the risk bears then:
  the share it holds in the reference of its project, as the register totals an occurred or a
  dismissed risk (WF-RIS-0040), nought without a reference;
- the identified risks of the revisions of several projects not reviewed since an instant each
  (``unreviewed``), among the reviews the revision presents: its own and those of the revisions
  marked before it (EP-08, "Tables et migrations"), its declaration the first of them.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Uuid, and_, any_, column, func, literal, select, values

from waterfall.core.estimate.interface import risk_base
from waterfall.core.projects.interface import NOBODY, project_facts
from waterfall.core.revisions.interface import marked_revisions_of
from waterfall.core.risks.commands import DISMISSED, IDENTIFIED, OCCURRED, state_named
from waterfall.core.risks.reading import NOUGHT, read_context, risk_view, seen_revisions
from waterfall.core.risks.registering import found_in
from waterfall.core.risks.sharing import shares_of
from waterfall.core.risks.tables import RiskEvaluation, RiskReview
from waterfall.platform.database import UtcDateTime

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.risks.views import RiskState


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    """A risk of a revision as the portfolio reads it, its figures those of the register."""

    risk_id: UUID
    label: str
    probability: Decimal
    severity: Decimal
    provision_amount: Decimal
    state: RiskState
    # Both null out of the state occurred.
    occurrence_cost: Decimal | None
    occurred_reestimated_amount: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioRisks:
    """The risks of a revision, in the order of their declaration, and the base of their project.

    ``base`` is what the matrix relates a severity to (WF-REF-0160): the budget of the reference,
    provisions left out, or before a reference the total of the revision.
    """

    base: Decimal
    risks: tuple[PortfolioRisk, ...]


@dataclass(frozen=True, slots=True)
class RiskOutcome:
    """A risk moved to occurred or to dismissed by a review of a day, and the provision it bears."""

    project_id: UUID
    risk_id: UUID
    reviewed_on: date
    state: RiskState
    provision_amount: Decimal


@dataclass(frozen=True, slots=True)
class ReviewWindow:
    """What is asked of the reviews of a project: its revision, and the instant they count from."""

    revision_id: UUID
    since: datetime


def survey(session: Session, project_id: UUID, revision_id: UUID) -> PortfolioRisks:
    """Give the risks a revision holds, read as the register reads them, and the base.

    A revision that holds no risk gives none, and its base all the same.
    """
    founds = found_in(session, project_id, revision_id, None)
    if not founds:
        return PortfolioRisks(risk_base(session, project_id, revision_id), ())
    context = read_context(session, project_id, founds)
    risks: list[PortfolioRisk] = []
    for found in founds:
        view = risk_view(session, project_id, found, NOBODY, context)
        risks.append(
            PortfolioRisk(
                risk_id=view.risk_id,
                label=view.label,
                probability=view.probability,
                severity=view.severity,
                provision_amount=view.provision_amount,
                state=view.state,
                occurrence_cost=view.occurrence_cost,
                occurred_reestimated_amount=view.occurred_reestimated_amount,
            )
        )
    return PortfolioRisks(context.bases[revision_id], tuple(risks))


def outcomes(
    session: Session, project_ids: Collection[UUID], first: date, last: date
) -> list[RiskOutcome]:
    """Give the risks of the projects named moved to occurred or dismissed in a period of days.

    From ``first`` to ``last``, both included. A review moves a risk when its state is not the one
    of the review before it, of whatever revision, in the order of their days then of their
    instants: the reviews of a risk are never copied, and those of the revisions not abandoned are
    its history. One statement for the reviews, then one for the reference and one for its shares
    by project that has an outcome. In the order of the projects, of the days, of the risks.
    """
    if not project_ids:
        return []
    order = (RiskReview.reviewed_on, RiskReview.created_at, RiskReview.id)
    before = func.lag(RiskReview.state).over(
        partition_by=(RiskReview.project_id, RiskReview.risk_id), order_by=order
    )
    history = (
        select(
            RiskReview.project_id,
            RiskReview.risk_id,
            RiskReview.reviewed_on,
            RiskReview.state,
            before.label("before"),
        )
        .where(RiskReview.project_id.in_(list(project_ids)), RiskReview.reviewed_on <= last)
        .subquery()
    )
    rows = session.execute(
        select(history.c.project_id, history.c.risk_id, history.c.reviewed_on, history.c.state)
        .where(
            history.c.reviewed_on >= first,
            history.c.state.in_((OCCURRED, DISMISSED)),
            history.c.before.is_distinct_from(history.c.state),
        )
        .order_by(history.c.project_id, history.c.reviewed_on, history.c.risk_id)
    ).all()
    shares: dict[UUID, dict[UUID, Decimal]] = {}
    for project_id in dict.fromkeys(row.project_id for row in rows):
        reference = project_facts(session, project_id).reference_revision_id
        shares[project_id] = {} if reference is None else shares_of(session, project_id, reference)
    return [
        RiskOutcome(
            project_id=row.project_id,
            risk_id=row.risk_id,
            reviewed_on=row.reviewed_on,
            state=state_named(row.state),
            provision_amount=shares[row.project_id].get(row.risk_id, NOUGHT),
        )
        for row in rows
    ]


def unreviewed(
    session: Session, windows: Mapping[UUID, ReviewWindow]
) -> dict[UUID, frozenset[UUID]]:
    """Give, by project, the risks its window's revision holds identified with no review since.

    A review made at ``since`` or after, among those the revision presents: its own and those of
    the revisions marked before it (``seen_revisions``), a marked revision presenting none made
    after its marking. A project with no such risk has no entry. One statement for the marked
    revisions of all the projects, one for their risks: never one by project.
    """
    if not windows:
        return {}
    marked = marked_revisions_of(session, list(windows))
    seen: set[UUID] = set()
    for project_id, window in windows.items():
        seen |= seen_revisions(dict(marked[project_id]), window.revision_id)
    bounds = values(
        column("project_id", Uuid),
        column("revision_id", Uuid),
        column("since", UtcDateTime),
        name="bounds",
    ).data([(each, window.revision_id, window.since) for each, window in windows.items()])
    reviewed = (
        select(literal(1))
        .where(
            RiskReview.project_id == RiskEvaluation.project_id,
            RiskReview.risk_id == RiskEvaluation.risk_id,
            RiskReview.revision_id == any_(literal(sorted(seen), ARRAY(Uuid))),
            RiskReview.created_at >= bounds.c.since,
        )
        .exists()
    )
    rows = session.execute(
        select(RiskEvaluation.project_id, RiskEvaluation.risk_id)
        .join(
            bounds,
            and_(
                bounds.c.project_id == RiskEvaluation.project_id,
                bounds.c.revision_id == RiskEvaluation.revision_id,
            ),
        )
        .where(RiskEvaluation.state == IDENTIFIED, ~reviewed)
    )
    found: dict[UUID, set[UUID]] = {}
    for project_id, risk_id in rows:
        found.setdefault(project_id, set()).add(risk_id)
    return {project_id: frozenset(risks) for project_id, risks in found.items()}
