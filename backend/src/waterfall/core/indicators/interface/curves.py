# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a project, on a scope (``getCostCurve``, ``getEarnedValueCurves``; US-1690).

The cumulative costs — the reference budget, the actual cost, the projection of the project
manager —, with or without the payment delays, which give the cash-out (WF-IND-0100); the planned
value, the earned value and the actual cost (WF-IND-0110): one point by end of month, the date of
the computation a point besides. Computed on the current day (US-1690/L2), or read as a marking
kept them (US-1690/L3). Given the cache of the process, the curves of the day are read in the entry
of their scope for the key of the project (US-1720/L2; one entry by scope, US-2420, #3628).

Declared by US-1660/L1, the socle of EP-10; filled by US-1690/L2 for the current day.
"""

from typing import TYPE_CHECKING

from waterfall.core.indicators.caching import cached_scopes
from waterfall.core.indicators.curving import (
    cost_curve_document,
    earned_value_curves_document,
    read_curves,
)
from waterfall.core.indicators.interface.project_indicators import day_reading
from waterfall.core.indicators.interface.stored_documents import kept_revision, stored_document
from waterfall.core.projects.interface import current_day
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.core.indicators.interface.reading import IndicatorsReading
    from waterfall.platform.cache import IndicatorsCache


def _kept_curves(
    session: Session, project_id: UUID, asked: IndicatorsReading, kind: IndicatorKind
) -> Document:
    """Give the curves a marking kept, of the marked revision named or of the date asked.

    As the marking wrote them, ``is_stored`` true; the 409 ``STATE_FORBIDS_OPERATION`` when the
    revision kept none — marked before In progress, or before the subproject existed.
    """
    revision_id = kept_revision(session, project_id, asked.revision_id, asked.as_of)
    found = stored_document(session, revision_id, kind, asked.scope)
    if found is None:
        raise ConflictError(STATE_FORBIDS_OPERATION)
    return found


def _day_curve(
    session: Session,
    project_id: UUID,
    asked: IndicatorsReading,
    kind: IndicatorKind,
    cache: IndicatorsCache | None,
) -> Document:
    """Give a curve of a kind on the scope a reading asks: of the day, or as a marking kept it.

    The refusals are those of ``getProjectIndicators``. The curve of the day is read in ``cache``
    when one is given (US-1720/L2), drawn on the current revision, or on the last marked one
    without it; a marked revision named, or a date, reads what its marking kept.
    """
    found = day_reading(session, project_id, asked)
    if found is None:
        return _kept_curves(session, project_id, asked, kind)
    basis, context, scope = found.basis, found.context, asked.scope
    if cache is not None:
        return cached_scopes(session, basis, context, (scope,), cache)[scope][kind]
    reading = read_curves(session, basis, current_day(context.computed_at), scope)
    if kind == "earned_value_curves":
        return earned_value_curves_document(reading, context)
    return cost_curve_document(reading, context, payment_delays=kind != "cost_curve")


def cost_curve(
    session: Session,
    project_id: UUID,
    asked: IndicatorsReading,
    *,
    payment_delays: bool,
    cache: IndicatorsCache | None = None,
) -> Document:
    """Give the cumulative costs of a project on a scope, shifted by the payment delays or not.

    The reference budget, the actual cost up to the day, then the projection of the project
    manager; computed on the current revision, or on the last marked one without it, the refusals
    those of ``project_indicators`` (WF-IND-0100).
    """
    kind: IndicatorKind = "cost_curve_payment_delays" if payment_delays else "cost_curve"
    return _day_curve(session, project_id, asked, kind, cache)


def earned_value_curves(
    session: Session,
    project_id: UUID,
    asked: IndicatorsReading,
    cache: IndicatorsCache | None = None,
) -> Document:
    """Give the planned value, the earned value and the actual cost of a project on a scope.

    Computed on the current revision, or on the last marked one without it, the refusals those of
    ``project_indicators`` (WF-IND-0110).
    """
    return _day_curve(session, project_id, asked, "earned_value_curves", cache)
