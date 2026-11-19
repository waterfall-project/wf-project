# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The coverage of the risks of a revision, private to the module (``getProjectRiskCoverage``).

The reserve is the one the reference of the project conserves (``sharing.reserve_of``, M-01),
whichever revision is read; the provisions left are those of the risks the revision identifies,
their severity weighted by their probability, to the cent; the cost of the occurred is the sum of
their costs at occurrence, which nothing changes after the occurrence; the variance is the reserve
less the two (WF-RIS-0050). What the lines that came from the occurred risks are re-estimated at
is shown beside, outside the variance (#1761).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.interface import Coverage, round_to_cent, structure_amounts
from waterfall.core.revisions.interface import read_revision_for
from waterfall.core.risks.commands import IDENTIFIED, OCCURRED
from waterfall.core.risks.reading import occurred_amounts
from waterfall.core.risks.sharing import reserve_of
from waterfall.core.risks.tables import RiskEvaluation

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

NOUGHT = Decimal("0.00")


def coverage_of(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project; 404 for a revision unknown."""
    read = read_revision_for(session, project_id, revision_id)
    reserve = reserve_of(session, project_id, read.reference_revision_id)
    evaluations = session.scalars(
        select(RiskEvaluation).where(
            RiskEvaluation.project_id == project_id,
            RiskEvaluation.revision_id == read.revision_id,
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
        by_risk = occurred_amounts(session, project_id, read.revision_id)
        reestimated = sum((by_risk.get(each.risk_id, NOUGHT) for each in occurred), NOUGHT)
    return Coverage(reserve, remaining, cost, reestimated, reserve - (remaining + cost))
