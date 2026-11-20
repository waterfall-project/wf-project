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
- the identified risks of a revision reviewed since an instant (``reviewed``), among the reviews
  the revision presents: its own and those of the revisions marked before it (EP-08, "Tables et
  migrations"), its declaration the first of them.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from waterfall.core.estimate.interface import risk_base
from waterfall.core.projects.interface import Viewer, project_facts
from waterfall.core.revisions.interface import marked_revisions_at
from waterfall.core.risks.commands import DISMISSED, IDENTIFIED, OCCURRED, state_named
from waterfall.core.risks.reading import NOUGHT, read_context, risk_view, seen_revisions
from waterfall.core.risks.registering import found_in
from waterfall.core.risks.sharing import shares_of
from waterfall.core.risks.tables import RiskEvaluation, RiskReview

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import date, datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.risks.views import RiskState

# Who reads the risks for the portfolio: no account, no permission (their commands are not read).
NOBODY = Viewer(UUID(int=0), ())


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


def reviewed(
    session: Session, project_id: UUID, revision_id: UUID, since: datetime
) -> frozenset[UUID]:
    """Give the risks a revision holds identified that a review it presents made since an instant.

    At ``since`` or after. The reviews of the revision and of those marked before it
    (``seen_revisions``): a marked revision presents none made after its marking.
    """
    seen = seen_revisions(marked_revisions_at(session, project_id), revision_id)
    identified = (
        select(RiskEvaluation.risk_id)
        .where(
            RiskEvaluation.project_id == project_id,
            RiskEvaluation.revision_id == revision_id,
            RiskEvaluation.state == IDENTIFIED,
        )
        .scalar_subquery()
    )
    return frozenset(
        session.scalars(
            select(RiskReview.risk_id)
            .where(
                RiskReview.project_id == project_id,
                RiskReview.revision_id.in_(list(seen)),
                RiskReview.risk_id.in_(identified),
                RiskReview.created_at >= since,
            )
            .distinct()
        )
    )
