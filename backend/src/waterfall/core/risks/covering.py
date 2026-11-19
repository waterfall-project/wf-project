# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The coverage of the risks of a revision, private to the module (``getProjectRiskCoverage``).

The reserve is the one the reference of the project conserves (``sharing.reserve_of``, M-01),
whichever revision is read; the provisions left are those of the risks the revision identifies,
their severity weighted by their probability, to the cent; the cost of the occurred is the sum of
their costs at occurrence, which nothing changes after the occurrence; the variance is the reserve
less the two (WF-RIS-0050). What the lines that came from the occurred risks are re-estimated at
is shown beside, outside the variance (#1761).

A marked revision keeps the figures of its risks — the provisions left, the cost of the occurred,
their re-estimated amount — and keeps them as marked (WF-DAT-0040); the reserve is not one of
them, written once by the designation of the reference and never computed again, so it is read of
the reference of the project as everywhere else, and the variance deduced (``conserved_coverage``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.interface import Coverage, round_to_cent, structure_amounts
from waterfall.core.projects.interface import project_facts
from waterfall.core.risks.commands import IDENTIFIED, OCCURRED
from waterfall.core.risks.reading import NOUGHT, occurred_amounts
from waterfall.core.risks.sharing import reserve_of
from waterfall.core.risks.tables import RiskEvaluation

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session


def _reserve(session: Session, project_id: UUID) -> Decimal:
    """Give the reserve the reference of the project conserves."""
    return reserve_of(session, project_id, project_facts(session, project_id).reference_revision_id)


def coverage_of(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project, which the caller has read."""
    reserve = _reserve(session, project_id)
    evaluations = session.scalars(
        select(RiskEvaluation).where(
            RiskEvaluation.project_id == project_id,
            RiskEvaluation.revision_id == revision_id,
            RiskEvaluation.state.in_((IDENTIFIED, OCCURRED)),
        )
    ).all()
    amounts = structure_amounts(
        session, project_id, {each.structure_id for each in evaluations if each.state == IDENTIFIED}
    )
    remaining = sum(
        (
            round_to_cent(amounts[each.structure_id] * each.probability)
            for each in evaluations
            if each.state == IDENTIFIED
        ),
        NOUGHT,
    )
    occurred = [each for each in evaluations if each.state == OCCURRED]
    cost = sum((each.occurrence_cost or NOUGHT for each in occurred), NOUGHT)
    reestimated = NOUGHT
    if occurred:
        by_risk = occurred_amounts(session, project_id, revision_id)
        reestimated = sum((by_risk.get(each.risk_id, NOUGHT) for each in occurred), NOUGHT)
    return Coverage(reserve, remaining, cost, reestimated, reserve - (remaining + cost))


def conserved_coverage(
    session: Session, project_id: UUID, kept: Mapping[str, str] | None
) -> dict[str, str] | None:
    """Give the coverage a marking kept with the reserve of the reference of the project.

    The figures of the risks stay as the marking kept them; the reserve is the one the reference
    conserves, which a revision marked before it was designated could not keep, and the variance is
    deduced from it. A document that kept no coverage, or one whose figures are missing, gives
    none (#4183): the caller computes the coverage at the reading, as it does for a revision whose
    marking kept nothing.
    """
    if kept is None or "remaining_provisions" not in kept or "occurred_cost" not in kept:
        return None
    reserve = _reserve(session, project_id)
    left = Decimal(kept["remaining_provisions"])
    cost = Decimal(kept["occurred_cost"])
    return {
        **kept,
        "reserve": format(reserve, "f"),
        "coverage_variance": format(reserve - (left + cost), "f"),
    }
