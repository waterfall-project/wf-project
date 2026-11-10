# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line reestimated, and the remaining to commit a revision copies of the review before (US-1580).

``set_line_remaining`` writes the figures of a line of a task not completed by the function that
writes the estimate (``update_line``), marks its re-estimation and keeps its reason; a remaining set
to zero on the last open line of a task completes it (``setLineRemaining``, US-1580/L2).
``copy_previous`` is the second copy the estimate registers (``register_copy``), after that of the
lines: a line copied from a revision marked in the state In progress receives the figures and the
reestimated amount of its source as its remaining to commit before the review (``previous_*``),
none from a revision marked before (EP-09, "Ce que le cadrage décide").

Declared by US-1580/L1. ``copy_previous`` is registered without effect: it copies nothing until
US-1580/L2 fills it; ``set_line_remaining`` raises ``NotImplementedError`` naming that story, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionCopy


def set_line_remaining(session: Session, project_id: UUID, node_id: UUID) -> None:
    """Reestimate a line at the counter read, and mark it (``setLineRemaining``)."""
    msg = "set_line_remaining is filled by US-1580/L2"
    raise NotImplementedError(msg)


def copy_previous(copy: RevisionCopy) -> None:
    """Give the lines copied the remaining to commit of their source: none yet."""
    del copy
