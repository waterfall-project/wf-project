# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of a task: not started, started, completed (``setTaskProgress``; EP-06, US-1410).

Declared by US-1380/L1; US-1410 fills it, and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def set_task_progress(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Set the state of a task, and give the nodes written (``setTaskProgress``)."""
    msg = "set_task_progress is filled by US-1410"
    raise NotImplementedError(msg)
