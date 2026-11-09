# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks (US-1510).

``estimate_indicators`` (``getEstimateIndicators``) and ``missing_rates`` (``getMissingRates``)
read the lines of a revision and its rates, and write nothing: the indicators are sums of the
amounts the lines keep, computed from the lines of the main structure of the revision named, else
the current one, else the last one marked (``indicating``).
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.indicating import (
    AmountByKey,
    EstimateIndicators,
    Figure,
    IndicatorsAsked,
    MissingRate,
    estimate_indicators_of,
    missing_rates_of,
)
from waterfall.core.revisions.interface import read_revision_for

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

__all__ = [
    "AmountByKey",
    "EstimateIndicators",
    "Figure",
    "IndicatorsAsked",
    "MissingRate",
    "estimate_indicators",
    "missing_rates",
]


def estimate_indicators(
    session: Session, project_id: UUID, asked: IndicatorsAsked
) -> EstimateIndicators:
    """Give the indicators of the estimate of a revision (``getEstimateIndicators``).

    Refused if the revision is unknown (404), then if the scope names a subproject the project
    does not have (422 ``VALIDATION_FAILED``, ``UNKNOWN_SUBPROJECT`` on ``/query/scope``).
    """
    return estimate_indicators_of(session, project_id, asked)


def missing_rates(
    session: Session, project_id: UUID, revision_id: UUID | None
) -> tuple[MissingRate, ...]:
    """Give the categories a revision employs without a rate for its year of reference.

    The revision named, else the current one, else the last one marked (``getMissingRates``); 404
    if it is unknown. A rate is the one the revision keeps or the reference's for the year.
    """
    return missing_rates_of(
        session, project_id, read_revision_for(session, project_id, revision_id)
    )
