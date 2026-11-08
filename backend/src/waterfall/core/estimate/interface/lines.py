# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of an estimate: a line changed, the question the designation asks, the witness's.

``update_line`` writes what is sent of a line at the counter read, in the frame of a write of the
planning — its revision judged, its entry of the history, the lock of its structure (409
``task_not_completed`` on the main structure under a completed task, #1767) — and prices it again
in its transaction (``updateEstimateLine``, US-1490/L3); EP-09 extends it for the remaining to
commit (``setLineRemaining``). ``revision_has_lines`` answers the designation of a reference,
whether a revision bears a line (``register_tasks_and_lines``, ``lines``, WF-CYC-0030);
``load_lines`` writes the lines of a revision of the witness at the identifiers and the instant it
imposes (US-1570).
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.writing import change_line
from waterfall.core.planning.interface import FacetChange, revision_bears, write_facet

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.planning.interface import NodesWritten, Place, Writer

LINE = "estimate_line"


def update_line(
    session: Session, place: Place, node_id: UUID, entry: LineEntry, writer: Writer
) -> NodesWritten:
    """Write what is sent of a line at the counter read, priced again (``updateEstimateLine``).

    Refused as a write of the tree is (404, 409, 412), then as the line judges what is sent (422,
    ``entries``), a role changed judged on the hours of its task (``TASK_WITHOUT_WORKING_HOURS``)
    and its rate found (``HOURLY_RATE_MISSING``); nothing is written then. A role changed changes
    the calendar of the task, which is redated with its successors (``rescheduled``), and the lines
    whose amounts move are given back (``reinflated``).
    """
    if entry.lock_version is None:
        msg = "a modification carries the counter it read"
        raise ValueError(msg)
    change = FacetChange(node_id, entry.lock_version, lambda write: change_line(write, entry))
    return write_facet(session, place, change, writer)


def revision_has_lines(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears a line of estimate (WF-CYC-0030)."""
    return revision_bears(session, revision_id, LINE)


def load_lines(session: Session, revision_id: UUID) -> None:
    """Write the lines of a revision of the witness, at the identifiers and the instant imposed."""
    msg = "load_lines is filled by US-1570"
    raise NotImplementedError(msg)
