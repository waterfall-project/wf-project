# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the projects ask the actual costs of a subproject (WF-PRJ-0050, WF-CRE-0020; US-1610/L3).

``subproject_has_actual_costs`` tells whether a line of cost is imputed to a subproject — its
deletion refused, ``has_actual_costs`` of the list of the subprojects and its filter —;
``impute_waiting_lines`` imputes to a subproject just created the lines of its project that wait for
its code, in the transaction of the creation. US-1610/L3 declares ``register_cost_facts`` in the
interface of the projects and fills it with them; the recoding of a subproject calls neither
(EP-09, "Ce que le cadrage décide").

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def subproject_has_actual_costs(session: Session, subproject_id: UUID) -> bool:
    """Tell whether a line of the actual costs is imputed to a subproject."""
    msg = "subproject_has_actual_costs is filled by US-1610/L3"
    raise NotImplementedError(msg)


def impute_waiting_lines(
    session: Session, project_id: UUID, subproject_id: UUID, code: str
) -> None:
    """Impute to a subproject created the lines of its project that wait for its code."""
    msg = "impute_waiting_lines is filled by US-1610/L3"
    raise NotImplementedError(msg)
