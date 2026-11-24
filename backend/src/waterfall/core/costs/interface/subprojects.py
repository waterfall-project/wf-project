# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the projects ask the actual costs of a subproject (WF-PRJ-0050, WF-CRE-0020; US-1610/L3).

``subproject_has_actual_costs`` gives, of the subprojects named, those a line of cost is imputed
to, tracked or excluded — their deletion refused, ``has_actual_costs`` of the list of the
subprojects, its filter and its sort, and the subproject a line of a started task cannot leave
(``SUBPROJECT_HAS_ACTUAL_COSTS``, EP-07) —, which fills ``register_cost_facts`` of the projects, at
the import of this interface. Neither the creation nor the recoding of a subproject imputes a line:
only the reimport of its extraction does (WF-CRE-0020; #3966, EP-09 D-10).
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


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
