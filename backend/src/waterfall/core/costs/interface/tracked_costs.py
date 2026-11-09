# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual cost of a project: the sums of its tracked lines, which the indicators read.

``actual_cost_by_subproject`` sums the tracked lines of a project by the subproject they are
imputed to, the lines imputed to the project alone under ``None`` (``unassigned``): the indicators
of the remaining to commit read it (US-1600). ``actual_costs_until`` sums the tracked lines of a
scope whose document is dated on or before a day, as known at the reading: the indicators of the
project read it (EP-10), served by US-1610/L2, which applies the imports (EP-09, "Ce que le cadrage
laisse à EP-10"). An excluded line enters neither (WF-CRE-0030).

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads; each raises
``NotImplementedError`` naming the story that fills it.
"""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

# The lines imputed to the project alone: without a subproject part in their WBS element, or with a
# code no subproject bears (WF-CRE-0020).
UNASSIGNED = "unassigned"
# The lines a sum keeps: those of the whole project (``None``), of a subproject (its identifier),
# or of the project alone (``UNASSIGNED``).
type CostScope = UUID | Literal["unassigned"] | None


def actual_cost_by_subproject(session: Session, project_id: UUID) -> Mapping[UUID | None, Decimal]:
    """Give the sum of the tracked lines of a project by subproject, ``None`` the project alone."""
    msg = "actual_cost_by_subproject is filled by US-1600"
    raise NotImplementedError(msg)


def actual_costs_until(
    session: Session, project_id: UUID, until: date, scope: CostScope
) -> Decimal:
    """Give the sum of the tracked lines of a scope of a project dated on or before ``until``."""
    msg = "actual_costs_until is filled by US-1610/L2"
    raise NotImplementedError(msg)
