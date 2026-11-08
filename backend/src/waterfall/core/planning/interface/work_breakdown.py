# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells the work breakdown of the tasks attached to it (WF-PLA-0170).

Registered at the import of the interface in the registry of the projects
(``register_attachments``): whether a task of a marked revision bears a work package or an order
item, and the withdrawal of an element from the tasks of the current revision, which
``set_work_breakdown`` asks of an element it removes.

Declared by US-1380/L1, without effect until US-1380/L3 fills them with the attachment of a task.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def work_breakdown_item_cited(session: Session, item_id: UUID) -> bool:
    """Tell whether a task of a marked revision bears an element of the work breakdown.

    None does until US-1380/L3 attaches tasks.
    """
    del session, item_id
    return False


def detach_work_breakdown_item(session: Session, project_id: UUID, item_id: UUID) -> None:
    """Withdraw an element of the work breakdown from the tasks of the current revision.

    Nothing until US-1380/L3 attaches tasks.
    """
    del session, project_id, item_id
