# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates of the witness, by category and year.

``volume/hourly_rate_grid.json``: the grid, a row per category, a cell per year of its columns
(an empty one is a year without a rate). Written by ``set_hourly_rate``, once per cell, after the
categories they belong to. The slice is held when every category the grid gives a rate to already
bears one.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.api.contract.models import HourlyRateGrid
from waterfall.core.cost_settings.interface import category_is_rated, set_hourly_rate
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    rows = witness.read("volume/hourly_rate_grid.json", HourlyRateGrid).rows
    rated = [row for row in rows if any(cell is not None for cell in row.cells)]
    imposed = {row.cost_category_id.root for row in rated}
    if is_loaded(imposed, category_is_rated(session, imposed)):
        return False
    for row in rated:
        for cell in row.cells:
            if cell is not None:
                key = (row.cost_category_id.root, cell.year.root)
                set_hourly_rate(session, key, Decimal(cell.amount.root), None, witness.act)
    return bool(rated)
