# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (US-1530; US-2320).

``compare_revisions`` (``compareRevisions``) reads the main structures of the revision read,
current or marked, and of a marked base of its project, matched by lineage, as ``listNodes`` reads
a structure — the tree of the revision read, each node marked and with what its base carried of
what differs, the removed ones at the place they had —, and the differences of their amounts by
nature and by subproject, each line under the key it carries in each revision (#1751). It writes
nothing, and prices nothing again: the lines of a marked revision are read on the amounts and the
images it kept (US-1500), those of the current one as they are.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.comparing import compare

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.comparing import Comparison, ComparisonAsked, Written


def compare_revisions(
    session: Session, project_id: UUID, asked: ComparisonAsked, written: Written
) -> Comparison:
    """Compare a revision with a marked base; or refuse (404, then 409 for a base not marked).

    ``written`` how the reader writes a node whole (``Node``), whose values the union compares.
    """
    return compare(session, project_id, asked, written)
