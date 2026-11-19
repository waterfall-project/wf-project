# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the key of the cache of the indicators reads of the content of a revision (US-1720/L2).

The number of its nodes, of its tasks and of its links, and the last ``updated_at`` of its nodes,
which a write of a task, of its state or of its dates moves on with its node: a write of a node,
of a state or of a link changes them, and with them the key of the indicators of the day (EP-10,
"Le cache"); no write of the planning calls the cache. A link has no instant of its own: a link
added or removed changes the number, a link changed redates its structure, whose counter the key
reads beside this stamp. The bases of the differentials are not counted (US-3050).

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1720/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.interface import not_a_base

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ContentStamp:
    """How many nodes, tasks and links a revision holds, and the last instant a node was written."""

    nodes: int
    tasks: int
    links: int
    updated_at: datetime | None


def revision_content_stamp(session: Session, project_id: UUID, revision_id: UUID) -> ContentStamp:
    """Give the stamp of the nodes, the tasks and the links of a revision, in one statement.

    The bases of its differentials are left out, which no indicator reads (US-3050): a base is
    priced and redated with the other structures, and moves the stamp no further than they do.
    """
    of_revision = (
        Node.project_id == project_id,
        Node.revision_id == revision_id,
        not_a_base(Node.structure_id, project_id, revision_id),
    )
    nodes = select(func.count()).select_from(Node).where(*of_revision)
    tasks = (
        select(func.count())
        .select_from(Task)
        .join(Node, (Node.project_id == Task.project_id) & (Node.id == Task.node_id))
        .where(Task.project_id == project_id, *of_revision)
    )
    links = (
        select(func.count())
        .select_from(TaskLink)
        .where(
            TaskLink.project_id == project_id,
            TaskLink.revision_id == revision_id,
            not_a_base(TaskLink.structure_id, project_id, revision_id),
        )
    )
    last = select(func.max(Node.updated_at)).where(*of_revision)
    row = session.execute(
        select(
            nodes.scalar_subquery(),
            tasks.scalar_subquery(),
            links.scalar_subquery(),
            last.scalar_subquery(),
        )
    ).one()
    return ContentStamp(nodes=row[0], tasks=row[1], links=row[2], updated_at=row[3])
