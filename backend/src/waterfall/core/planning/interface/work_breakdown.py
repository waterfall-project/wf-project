# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells the work breakdown of the tasks attached to it (WF-PLA-0170).

Registered at the import of the interface in the registry of the projects
(``register_attachments``): whether a task of a marked revision bears a work package or an order
item, and the withdrawal of an element from the tasks of the current revision, which
``set_work_breakdown`` asks of an element it removes.

Declared by US-1380/L1, filled by US-1380/L3: a task of a revision other than the current one of
its project is one of a marked revision — an abandoned revision leaves no task —; the tasks of the
current revision lose the element, those of the marked ones keep it, which their revision freezes.
"""

from typing import TYPE_CHECKING

from sqlalchemy import or_, select, update

from waterfall.core.planning.tables import Node, Task
from waterfall.core.revisions.interface import current_revision

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def work_breakdown_item_cited(session: Session, item_id: UUID) -> bool:
    """Tell whether a task of a marked revision bears an element of the work breakdown."""
    bearing = session.execute(
        select(Node.project_id, Node.revision_id)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(or_(Task.work_package_id == item_id, Task.order_item_id == item_id))
        .distinct()
    ).all()
    return any(
        revision_id != current_revision(session, project_id) for project_id, revision_id in bearing
    )


def detach_work_breakdown_item(session: Session, project_id: UUID, item_id: UUID) -> None:
    """Withdraw an element of the work breakdown from the tasks of the current revision."""
    current = current_revision(session, project_id)
    if current is None:
        return
    of_current = select(Node.id).where(Node.project_id == project_id, Node.revision_id == current)
    for column in (Task.work_package_id, Task.order_item_id):
        session.execute(
            update(Task)
            .where(Task.project_id == project_id, column == item_id, Task.node_id.in_(of_current))
            .values({column.key: None})
            .execution_options(synchronize_session=False)
        )
