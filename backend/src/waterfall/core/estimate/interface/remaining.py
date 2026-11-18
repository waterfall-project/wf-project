# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line reestimated (US-1580).

``set_line_remaining`` writes the figures of a line of a task not completed by the function that
writes the estimate (``change_line``), marks its re-estimation and keeps its reason; a remaining set
to zero on the last open line of a task completes it, by the planning, in the same write
(``write_remaining``, ``setLineRemaining``, WF-RAE-0040). The remaining to commit before the review
a line copied from a revision marked in the state In progress receives (``previous_*``, EP-09, "Ce
que le cadrage décide") was a second copy the estimate registered, ``copy_previous``; the copy of
the lines writes it since US-2240/L2, in its one statement.

Declared by US-1580/L1; filled by US-1580/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.remaining import reviewing
from waterfall.core.planning.interface import RemainingChange, write_remaining

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.planning.interface import NodesWritten, Place, Writer


@dataclass(frozen=True, slots=True)
class LineRemaining:
    """What a re-estimate sends of a line (``RemainingUpdate``).

    ``figures`` the figures of ``reestimated_amount_basis``, those sent named (``LineEntry.sent``),
    at the counter read (``LineEntry.lock_version``); ``reason`` kept with the line, none when not
    sent; ``completed_on`` the date its task completes at, if the entry completes it.
    """

    figures: LineEntry
    reason: str | None = None
    completed_on: date | None = None


def set_line_remaining(
    session: Session, place: Place, node_id: UUID, entry: LineRemaining, writer: Writer
) -> NodesWritten:
    """Re-estimate a line at the counter read, mark it, and complete its task by it if it must.

    Refused as ``write_remaining`` judges the line and its entry (404, 412, 409), then as the entry
    of the estimate judges its figures (422); the task whose last open line it sets to nought is
    completed at ``completed_on``, 422 ``COMPLETION_DATE_REQUIRED`` without one. Nothing is written
    on a refusal.
    """
    counter = entry.figures.lock_version
    if counter is None:
        msg = "a re-estimate carries the counter it read"
        raise ValueError(msg)
    change = RemainingChange(
        node_id,
        counter,
        lambda write: reviewing.reestimate(write, entry.figures, entry.reason),
        reviewing.keeps_open,
        entry.completed_on,
    )
    return write_remaining(session, place, change, writer)
