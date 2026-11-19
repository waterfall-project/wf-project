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
differential and its base, the structure read being the differential (US-3050/L2).
``differential_rows`` gives its numbering alone, the one calculation of the rows of a differential,
removed nodes included, which every other operation that names a row of it takes
(``resolveRowNumber``, the numbers of a write, the anchor of a paste).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.comparing import compare, compare_differential
from waterfall.core.estimate.uniting import REMOVED
from waterfall.core.planning.interface import NodeFilters

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.comparing import Comparison, ComparisonAsked, Written
    from waterfall.core.planning.interface import Place


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
    """Read a differential as a diff with its base (``listNodes``, US-3050).

    ``differences`` the marks ``difference`` keeps, none to keep them all; ``written`` how the
    reader writes a node whole, whose values the union compares. The totals are the differential's,
    the nodes it removes counted in none (WF-REV-0100, C-361).
    """
    return compare_differential(session, place, filters, differences, written)


@dataclass(frozen=True, slots=True)
class DifferentialRow:
    """A row of the tree a differential is read as: a node, its place, and whether it is removed.

    ``row_number``, ``level`` and ``position`` count the whole tree returned, the nodes the
    differential removes included (``Node``, WF-REV-0080); a removed node is its base's.
    """

    node_id: UUID
    row_number: int
    level: int
    position: int
    removed: bool


def differential_rows(
    session: Session, place: Place, written: Written
) -> tuple[DifferentialRow, ...]:
    """Give the rows of a differential as ``listNodes`` returns it, in their order.

    The union of the differential and of its base, no filter retaining a part of it: each node of
    it, a node removed at its place, with the row it is read at.
    """
    found = read_differential(session, place, NodeFilters(), None, written)
    return tuple(
        DifferentialRow(
            each.view.node_id,
            each.view.row_number,
            each.view.level,
            each.view.position,
            each.difference == REMOVED,
        )
        for each in found.items
    )
