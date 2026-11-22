# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The marked revisions a backup counts, and those it samples, which its test compares (US-2930).

The manifest of a backup says how many revisions are marked, and names a sample of them, the latest
marked, whose kept indicators it digests; the test of a restoration counts and digests them again
in the database restored (WF-EXP-0060).
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.revisions.tables import Revision

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

MARKED = "marked"


def count_marked_revisions(session: Session) -> int:
    """Give the number of the marked revisions of every project."""
    marked = select(func.count()).select_from(Revision).where(Revision.status == MARKED)
    return session.scalar(marked) or 0


def sampled_marked_revisions(session: Session, size: int) -> list[tuple[UUID, UUID]]:
    """Give the ``size`` latest marked revisions, each after its project: the latest first.

    Two marked at the same instant are ordered by their identifier, so that a sample read twice
    from the same state is the same.
    """
    latest = (
        select(Revision.project_id, Revision.id)
        .where(Revision.status == MARKED)
        .order_by(Revision.marked_at.desc(), Revision.id)
        .limit(size)
    )
    return [(project_id, revision_id) for project_id, revision_id in session.execute(latest)]
