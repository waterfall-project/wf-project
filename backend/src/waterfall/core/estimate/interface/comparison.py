# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (US-1530).

``compare_revisions`` (``compareRevisions``) reads the lines of two revisions by their lineage, and
writes nothing.

Declared by US-1490/L1; it raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def compare_revisions(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Compare a revision with another of its project, line by line."""
    msg = "compare_revisions is filled by US-1530"
    raise NotImplementedError(msg)
