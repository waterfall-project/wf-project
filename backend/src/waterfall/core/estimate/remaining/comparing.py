# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the remaining to commit is compared with, private to the module (US-1600).

The budget of the reference by subproject, the sum of the budgeted amounts of the lines of its main
structure, provisions left out (WF-IND-0020) — a line of the reference itself, budgeted by no
lineage, counting its re-estimated amount, as the lines are read (``budgeted_of``); the review
before a revision, the last revision marked before it once its project was In progress — an offer
marked in pricing is not one (WF-RAE-0020) —; and the lines of a revision grouped by the subproject
that bears them.
"""

from typing import TYPE_CHECKING

from waterfall.core.costs.interface import UNASSIGNED
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.remaining.reviewing import (
    first_passage,
    provisions_of,
    was_reviewed_at,
)
from waterfall.core.estimate.remaining.summing import NOUGHT
from waterfall.core.planning.interface import lines_of_structure
from waterfall.core.revisions.interface import aimed_structure, marked_revisions_at

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.tables import EstimateLine


def subproject_key(line: EstimateLine) -> str:
    """Give the key a line is counted under: its subproject, or ``unassigned``."""
    return UNASSIGNED if line.subproject_id is None else str(line.subproject_id)


def summed_by_subproject(
    lines: Iterable[EstimateLine], amounts: Mapping[UUID, Decimal]
) -> dict[str, Decimal]:
    """Give the sum of the amounts of the lines, by the subproject that bears each, in the lines."""
    found: dict[str, Decimal] = {}
    for line in lines:
        key = subproject_key(line)
        found[key] = found.get(key, NOUGHT) + amounts.get(line.node_id, NOUGHT)
    return found


def reference_budgets(session: Session, project_id: UUID, reference_id: UUID) -> dict[str, Decimal]:
    """Give the budget of the reference by subproject: its budgeted amounts, provisions left out."""
    structure_id = aimed_structure(session, project_id, reference_id, None)
    if structure_id is None:
        return {}
    lines = rows_of(session, project_id, lines_of_structure(session, project_id, structure_id))
    provisions = provisions_of(session, lines)
    budgeted = {line.node_id: budgeted_of(line) for line in lines if line.node_id not in provisions}
    return summed_by_subproject((line for line in lines if line.node_id in budgeted), budgeted)


def previous_review(session: Session, project_id: UUID, revision_id: UUID) -> UUID | None:
    """Give the last revision marked before the one read in the state In progress; none without.

    Those marked at or after the one read, if it is marked, are not before it; a revision still in
    progress is read after every marked one.
    """
    marks = marked_revisions_at(session, project_id)
    own = marks.get(revision_id)
    passage = first_passage(session, project_id)
    later = sorted(((at, each) for each, at in marks.items() if each != revision_id), reverse=True)
    for at, each in later:
        if (own is None or (at, each) < (own, revision_id)) and was_reviewed_at(passage, at):
            return each
    return None
