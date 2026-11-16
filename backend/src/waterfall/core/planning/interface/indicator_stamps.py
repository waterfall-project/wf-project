# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the key of the cache of the indicators reads of the content of a revision (US-1720/L2).

The number and the last ``updated_at`` of its nodes, its tasks and its links: a write of a node, of
a state or of a link changes them, and with them the key of the indicators of the day (EP-10, "Le
cache"); no write of the planning calls the cache.

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1720/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ContentStamp:
    """How many nodes, tasks and links a revision holds, and the last instant one was written."""

    count: int
    updated_at: datetime | None


def revision_content_stamp(session: Session, project_id: UUID, revision_id: UUID) -> ContentStamp:
    """Give the stamp of the nodes, the tasks and the links of a revision."""
    msg = "revision_content_stamp is filled by US-1720/L2"
    raise NotImplementedError(msg)
