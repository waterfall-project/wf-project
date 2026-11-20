# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the portfolio as the contract writes them (``PortfolioScope``, a row).

An amount is written to the cent as ``Money``, a share or a ratio without its trailing zeros as
``Decimal`` (``Percent``), an instant in universal time, a date in ISO form: the same writing as the
documents of the indicators, so that a row reads as the document it is formed of.
"""

from datetime import UTC
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import plain_decimal

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from waterfall.core.indicators.interface import Computable, Document
    from waterfall.core.portfolio.interface.scope import PortfolioScope
    from waterfall.core.portfolio.rows import ProjectRow


def money(amount: Decimal | None) -> str | None:
    """Write an amount to the cent, as ``Money`` of the contract; null stays null."""
    return None if amount is None else format(amount, "f")


def hours(amount: Decimal | None) -> str | None:
    """Write hours, or a capacity in hours, to the hundredth; null stays null."""
    return None if amount is None else format(amount, "f")


def percent(share: Decimal | None) -> str | None:
    """Write a share or a ratio without a useless zero, as ``Percent`` or ``Decimal``."""
    return None if share is None else plain_decimal(share)


def computable(figure: Computable) -> Document:
    """Write a ratio in the envelope of the contract (``Computable``): its value, or its reason."""
    return {
        "is_computable": figure.value is not None,
        "value": percent(figure.value),
        "reason": figure.reason,
    }


def instant(moment: datetime | None) -> str | None:
    """Write an instant in universal time as the contract does; null stays null."""
    if moment is None:
        return None
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def scope_document(scope: PortfolioScope) -> Document:
    """Write the scope a view retains (``PortfolioScope``)."""
    return {
        "states": list(scope.states),
        "as_of": scope.as_of.isoformat(),
        "from": None if scope.period_from is None else scope.period_from.isoformat(),
        "to": None if scope.period_to is None else scope.period_to.isoformat(),
        "org_node_id": None if scope.org_node_id is None else str(scope.org_node_id),
        "org_node_label": scope.org_node_label,
        "project_count": scope.project_count,
    }


def row_document(row: ProjectRow) -> Document:
    """Write a row of the list (``PortfolioProjectRow``)."""
    return {
        "project_id": str(row.project_id),
        "label": row.label,
        "code": row.code,
        "state": row.state,
        "can_open": row.can_open,
        "reference_budget": money(row.reference_budget),
        "current_estimate": money(row.current_estimate),
        "win_probability": percent(row.win_probability),
        "project_manager_projection": money(row.project_manager_projection),
        "delta_to_reference": money(row.delta_to_reference),
        "cost_index": None if row.cost_index is None else row.cost_index.document,
        "schedule_index": None if row.schedule_index is None else row.schedule_index.document,
        "last_marked_at": instant(row.last_marked_at),
    }
