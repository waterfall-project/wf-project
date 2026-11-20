# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio reads of the actual costs: the last import of each project (EP-11).

The health of the control of the projects flags a project In progress that has imported no cost
since its last marked revision (WF-PTF-0110): the instant of the last import applied of each
project, before an instant of its own — the marking its interval ends at, which a past date reads
as the imports stood then —, in one query.

Declared by US-2670/L1, the socle of EP-11; filled by US-2750.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Uuid, column, func, select, values

from waterfall.core.costs.tables import CostImport
from waterfall.platform.database import UtcDateTime

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


def last_imports(session: Session, before: Mapping[UUID, datetime]) -> dict[UUID, datetime]:
    """Give the instant of the last import applied up to the instant of each project, if any.

    ``before`` names each project with the instant its imports are read up to, itself included: an
    import applied at that very instant is counted, as the lower bound the caller compares it with
    is. A project that imported nothing up to its instant has no entry. One query for all of them.
    """
    if not before:
        return {}
    bounds = values(column("project_id", Uuid), column("before", UtcDateTime), name="bounds").data(
        list(before.items())
    )
    rows = session.execute(
        select(CostImport.project_id, func.max(CostImport.imported_at))
        .join(bounds, bounds.c.project_id == CostImport.project_id)
        .where(CostImport.imported_at <= bounds.c.before)
        .group_by(CostImport.project_id)
    )
    return dict(rows.all())
