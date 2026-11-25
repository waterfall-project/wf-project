# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the key of the cache of the indicators reads of the actual costs of a project (US-1720/L2).

The number of the imports applied to the project and the last instant one was
(``cost_import.imported_at``), the number of its lines of cost, the last instant one was written
(``cost_line.updated_at``) and the sum of their counters (``cost_line.lock_version``, #3629): an
import applied, a line excluded or reinstated change them, and with them the key of the indicators
of the day (EP-10, "Le cache"); no write of the actual costs calls the cache. The migration of the
codes (0047, #3966) deletes the lines that waited for a subproject: the sum of the counters falls
back, but their number falls too, below any number the project had since its last import — lines
are added by imports alone, and the number of the imports never falls —, so the key it gives was
never one of the project, and no entry kept before it is served after it. An import inserts its
entry and none is ever deleted: their number grows at each import, in its transaction, where its
instant, that of the start of its act, may be older than the last one committed.
``actual_costs_until`` and ``actual_cost_by_subproject`` serve the
indicators as they are (``tracked_costs``).
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
    """The imports of a project, the last, its lines of cost, the last written, their counters."""

    imports: int
    imported_at: datetime | None
    lines: int
    updated_at: datetime | None
    versions: int


def costs_stamp(session: Session, project_id: UUID) -> CostsStamp:
    """Give the stamp of the imports and of the lines of cost of a project, in one statement."""
    of_project = CostImport.project_id == project_id
    imports = select(func.count()).select_from(CostImport).where(of_project)
    imported = select(func.max(CostImport.imported_at)).where(of_project)
    lines = select(func.count()).select_from(CostLine).where(CostLine.project_id == project_id)
    last = select(func.max(CostLine.updated_at)).where(CostLine.project_id == project_id)
    versions = select(func.coalesce(func.sum(CostLine.lock_version), 0)).where(
        CostLine.project_id == project_id
    )
    row = session.execute(
        select(
            imports.scalar_subquery(),
            imported.scalar_subquery(),
            lines.scalar_subquery(),
            last.scalar_subquery(),
            versions.scalar_subquery(),
        )
    ).one()
    return CostsStamp(
        imports=row[0],
        imported_at=row[1],
        lines=row[2],
        updated_at=row[3],
        versions=int(row[4]),
    )
