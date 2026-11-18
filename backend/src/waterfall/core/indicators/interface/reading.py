# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a reading of the indicators asks: a revision, a scope, the instant of the reading.

The revision (``IndicatorsRevision``, ``AsOf``): neither named, the current revision on the current
day, or, without one, the last marked revision with the actual cost of the day; ``revision_id``, a
marked revision as its marking kept it; ``as_of``, the last revision marked on or before that day
among those that kept the indicators of the project (EP-10, "Le calcul des indicateurs"). The API
refuses the two together before any reading. The scope (``Scope``) is the project, the lines of the
project alone or a subproject, as the actual costs name it (``CostScope``). The instant is read by
the caller, never by the indicators; ``current_day`` gives its day in the time zone of the
installation (US-2200).

Declared by US-1660/L1; read by US-1660/L3 (the day), US-1670/L2 (a marked revision, a date) and
US-1690 (the curves).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from waterfall.core.costs.interface import CostScope


@dataclass(frozen=True, slots=True)
class IndicatorsReading:
    """What a reading asks: its scope, its instant, and a revision named, a day, or neither."""

    scope: CostScope
    at: datetime
    revision_id: UUID | None = None
    as_of: date | None = None
