# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (US-1530).

``compare_revisions`` (``compareRevisions``) reads the main structures of two marked revisions of
a project, matched by lineage, as ``listNodes`` reads a structure — the tree of the compared one,
each node marked, the removed ones at the place they had —, and the differences of their amounts
by nature and by subproject, each line under the key it carries in each revision (#1751). It
writes nothing, and prices nothing again: the lines are read on the amounts and the images their
revisions kept (US-1500).
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.comparing import compare

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.comparing import Comparison, ComparisonAsked


def compare_revisions(session: Session, project_id: UUID, asked: ComparisonAsked) -> Comparison:
    """Compare two marked revisions of a project; or refuse (404, then 409)."""
    return compare(session, project_id, asked)
