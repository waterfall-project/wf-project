# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a project, on a scope (``getCostCurve``, ``getEarnedValueCurves``; US-1690).

The cumulative costs — the reference budget, the actual cost, the projection of the project
manager —, with or without the payment delays, which give the cash-out (WF-IND-0100); the planned
value, the earned value and the actual cost (WF-IND-0110): one point by end of month, the date of
the computation a point besides. Computed on the current day (US-1690/L2), or read as a marking
kept them (US-1690/L3).

Declared by US-1660/L1, the socle of EP-10.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.interface.reading import IndicatorsReading


def cost_curve(
    session: Session, project_id: UUID, asked: IndicatorsReading, *, payment_delays: bool
) -> Document:
    """Give the cumulative costs of a project on a scope, shifted by the payment delays or not."""
    msg = "cost_curve is filled by US-1690/L2"
    raise NotImplementedError(msg)


def earned_value_curves(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the planned value, the earned value and the actual cost of a project on a scope."""
    msg = "earned_value_curves is filled by US-1690/L2"
    raise NotImplementedError(msg)
