# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the key of the cache of the indicators reads of the actual costs of a project (US-1720/L2).

The last instant an import was applied to the project (``cost_import.imported_at``), the number of
its lines of cost and the last instant one was written (``cost_line.updated_at``): an import
applied, a line excluded or reinstated, a line imputed to a subproject created change them, and
with them the key of the indicators of the day (EP-10, "Le cache"); no write of the actual costs
calls the cache. ``actual_costs_until`` and ``actual_cost_by_subproject`` serve the indicators as
they are (``tracked_costs``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.costs.tables import CostImport, CostLine

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class CostsStamp:
    """The last import of a project, how many lines of cost it holds, and the last one written."""

    imported_at: datetime | None
    lines: int
    updated_at: datetime | None


def costs_stamp(session: Session, project_id: UUID) -> CostsStamp:
    """Give the stamp of the imports and of the lines of cost of a project, in one statement."""
    imported = select(func.max(CostImport.imported_at)).where(CostImport.project_id == project_id)
    lines = select(func.count()).select_from(CostLine).where(CostLine.project_id == project_id)
    last = select(func.max(CostLine.updated_at)).where(CostLine.project_id == project_id)
    row = session.execute(
        select(imported.scalar_subquery(), lines.scalar_subquery(), last.scalar_subquery())
    ).one()
    return CostsStamp(imported_at=row[0], lines=row[1], updated_at=row[2])
