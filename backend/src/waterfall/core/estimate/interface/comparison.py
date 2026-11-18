# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (US-1530; US-2320), and a differential read.

``compare_revisions`` (``compareRevisions``) reads the main structures of the revision read,
current or marked, and of a marked base of its project, matched by lineage, as ``listNodes`` reads
a structure — the tree of the revision read, each node marked and with what its base carried of
what differs, the removed ones at the place they had —, and the differences of their amounts by
nature and by subproject, each line under the key it carries in each revision (#1751). It writes
nothing, and prices nothing again: the lines of a marked revision are read on the amounts and the
images it kept (US-1500), those of the current one as they are.

``read_differential`` (``listNodes`` of a differential, US-2550/L3) reads the same union between a
differential and the main structure of its revision, the structure read being the differential.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.comparing import compare, compare_differential

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.comparing import Comparison, ComparisonAsked, Written
    from waterfall.core.planning.interface import NodeFilters, Place


def compare_revisions(
    session: Session, project_id: UUID, asked: ComparisonAsked, written: Written
) -> Comparison:
    """Compare a revision with a marked base; or refuse (404, then 409 for a base not marked).

    ``written`` how the reader writes a node whole (``Node``), whose values the union compares.
    """
    return compare(session, project_id, asked, written)


def read_differential(
    session: Session,
    place: Place,
    filters: NodeFilters,
    differences: tuple[str, ...] | None,
    written: Written,
) -> Comparison:
    """Read a differential as a diff with the main structure of its revision (``listNodes``).

    ``differences`` the marks ``difference`` keeps, none to keep them all; ``written`` how the
    reader writes a node whole, whose values the union compares. The totals are the differential's,
    the nodes it removes counted in none (WF-REV-0100, C-361).
    """
    return compare_differential(session, place, filters, differences, written)
