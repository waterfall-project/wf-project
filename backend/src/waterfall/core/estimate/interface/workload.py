# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of an estimate: the hours of its lines spread over their tasks (US-1520).

``workload`` spreads the hours of the labour lines of a revision over the working hours of their
tasks, by role and by period, through the subpackage ``spreading``, which the planned value shares
(``planned_value``, re-exported by the interface); it writes nothing.

Declared by US-1490/L1; it raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def workload(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the load of the lines of a revision, by role and by period."""
    msg = "workload is filled by US-1520"
    raise NotImplementedError(msg)
