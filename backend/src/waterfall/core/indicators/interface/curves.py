# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a project, on a scope (``getCostCurve``, ``getEarnedValueCurves``; US-1690).

The cumulative costs — the reference budget, the actual cost, the projection of the project
manager —, with or without the payment delays, which give the cash-out (WF-IND-0100); the planned
value, the earned value and the actual cost (WF-IND-0110): one point by end of month, the date of
the computation a point besides. Computed on the current day (US-1690/L2), or read as a marking
kept them (US-1690/L3).

Declared by US-1660/L1, the socle of EP-10; filled by US-1690/L2 for the current day.
"""

from typing import TYPE_CHECKING

from waterfall.core.indicators.curving import (
    cost_curve_document,
    earned_value_curves_document,
    read_curves,
)
from waterfall.core.indicators.interface.project_indicators import day_reading
from waterfall.core.projects.interface import current_day

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.curving import CurveReading
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.interface.reading import IndicatorsReading
    from waterfall.core.indicators.shaping import Context


def _kept_curves(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the curves a marking kept, of the marked revision named or of the date asked."""
    msg = "_kept_curves is filled by US-1690/L3"
    raise NotImplementedError(msg)


def _read(
    session: Session, project_id: UUID, asked: IndicatorsReading
) -> tuple[Context, CurveReading] | None:
    """Refuse as ``getProjectIndicators`` does, then read what the curves of the day are drawn from.

    None when the reading asks a marked revision or a date, which a marking kept (US-1690/L3).
    """
    found = day_reading(session, project_id, asked)
    if found is None:
        return None
    day = current_day(found.context.computed_at)
    return found.context, read_curves(session, found.basis, day, asked.scope)


def cost_curve(
    session: Session, project_id: UUID, asked: IndicatorsReading, *, payment_delays: bool
) -> Document:
    """Give the cumulative costs of a project on a scope, shifted by the payment delays or not.

    The reference budget, the actual cost up to the day, then the projection of the project
    manager; computed on the current revision, or on the last marked one without it, the refusals
    those of ``project_indicators`` (WF-IND-0100).
    """
    read = _read(session, project_id, asked)
    if read is None:
        return _kept_curves(session, project_id, asked)
    return cost_curve_document(read[1], read[0], payment_delays=payment_delays)


def earned_value_curves(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the planned value, the earned value and the actual cost of a project on a scope.

    Computed on the current revision, or on the last marked one without it, the refusals those of
    ``project_indicators`` (WF-IND-0110).
    """
    read = _read(session, project_id, asked)
    if read is None:
        return _kept_curves(session, project_id, asked)
    return earned_value_curves_document(read[1], read[0])
