# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the projects ask the actual costs of a subproject (WF-PRJ-0050, WF-CRE-0020; US-1610/L3).

``subproject_has_actual_costs`` gives, of the subprojects named, those a line of cost is imputed
to, tracked or excluded — their deletion refused, ``has_actual_costs`` of the list of the
subprojects, its filter and its sort, and the subproject a line of a started task cannot leave
(``SUBPROJECT_HAS_ACTUAL_COSTS``, EP-07) —; ``impute_waiting_lines`` imputes to a subproject just
created the lines of its project that bear its code and no subproject, in the transaction of the
creation, under the lock of the project the creation holds, its author and its instant theirs.
Both fill ``register_cost_facts`` of the projects, at the import of this interface; the recoding of
a subproject calls neither (EP-09, "Ce que le cadrage décide", D-10).
"""

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def subproject_has_actual_costs(
    session: Session, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects named, those a line of cost is imputed to, excluded or not."""
    if not subproject_ids:
        return frozenset()
    imputed = (
        select(CostLine.subproject_id)
        .where(CostLine.subproject_id.in_(list(subproject_ids)))
        .distinct()
    )
    return frozenset(each for each in session.scalars(imputed) if each is not None)


def impute_waiting_lines(
    session: Session, project_id: UUID, subproject_id: UUID, code: str, act: Act
) -> None:
    """Impute to a subproject created the lines of its project that wait for its code.

    A line waits for a code when it bears it and no subproject: its WBS element named a code no
    subproject bore when it was imported (WF-CRE-0020). The code is compared as stored, as the
    import compares it; the lines of another project, or already imputed, are left as they are.
    """
    session.execute(
        update(CostLine)
        .where(
            CostLine.project_id == project_id,
            CostLine.subproject_code == code,
            CostLine.subproject_id.is_(None),
        )
        .values(subproject_id=subproject_id, updated_at=act.at, updated_by=act.author)
    )
