# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks (US-1510).

``estimate_indicators`` (``getEstimateIndicators``) and ``missing_rates`` (``getMissingRates``)
read the lines of a revision and its rates, and write nothing.

Declared by US-1490/L1; each raises ``NotImplementedError`` naming the story that fills it, and
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def estimate_indicators(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the indicators of the estimate of a revision (``getEstimateIndicators``)."""
    msg = "estimate_indicators is filled by US-1510"
    raise NotImplementedError(msg)


def missing_rates(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the categories a revision lacks a rate for, by year (``getMissingRates``)."""
    msg = "missing_rates is filled by US-1510"
    raise NotImplementedError(msg)
