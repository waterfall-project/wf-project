# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How many lines of cost the platform holds, which a backup counts and its test compares.

The manifest of a backup says it, and the test of a restoration counts them again in the database
restored (US-2930, WF-EXP-0060).
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def count_cost_lines(session: Session) -> int:
    """Give the number of the lines of cost of every project, in the tracked scope or not."""
    return session.scalar(select(func.count()).select_from(CostLine)) or 0
