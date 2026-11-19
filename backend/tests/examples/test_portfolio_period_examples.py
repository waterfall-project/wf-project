# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric example of a statistic of a period of the portfolio (US-2670/L3), no database.

From its fixture under ``fixtures/portfolio``: a transition is retained by its date, the bounds of
the period included (WF-CYC-0130), between the instants ``period_instants`` gives a scope — those
the offers closed in a period are read between (``offers_closed_between``). In the time zone of the
installation the tests run in, universal time.
"""

from calendar import monthrange
from datetime import date, datetime
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.portfolio.interface import PortfolioScope, period_instants

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _month(year: int, month: int) -> PortfolioScope:
    """Give the scope of a view read over a whole month, on its last day."""
    last = date(year, month, monthrange(year, month)[1])
    return PortfolioScope(("in_progress",), last, date(year, month, 1), last, None, None, 0)


@pytest.mark.requirement("WF-CYC-0130-A")
def test_an_offer_lost_on_15_march_is_closed_in_march_and_in_no_other_month(
    example: Callable[[str], Example],
) -> None:
    # « Un projet passé à Perdu le 15 mars compte parmi les offres closes de mars et d'aucun autre
    # mois. »
    data = example("WF-CYC-0130-A#72d37d732212")
    lost_at = datetime.fromisoformat(cast("str", data["lost_at"]))
    year = cast("int", data["year"])
    closed_in: list[int] = []
    for month in range(1, 13):
        instants = period_instants(_month(year, month))
        assert instants is not None
        if instants[0] <= lost_at < instants[1]:
            closed_in.append(month)
    assert closed_in == data["closed_in"]
