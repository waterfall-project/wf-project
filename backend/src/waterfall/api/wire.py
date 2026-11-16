# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the API writes a decimal and a work instant, as the contract has them.

Shared by the routes that give a start or a finish (``nodes``, ``workload``): one way to write each,
whatever the route.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from decimal import Decimal

    from waterfall.core.planning.interface import WorkInstant


def text_of(value: Decimal) -> str:
    """Give a decimal as the contract writes it: without exponent nor trailing zeros."""
    return format(value.normalize(), "f")


def instant_of(instant: WorkInstant) -> dict[str, Any]:
    """Give a start or a finish as the contract writes it (``WorkInstant``)."""
    return {"date": instant.day.isoformat(), "hours": text_of(instant.hours)}
