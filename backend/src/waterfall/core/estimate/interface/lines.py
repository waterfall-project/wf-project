# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of an estimate: a line changed, the question the designation asks, the witness's.

``update_line`` changes a line and prices it again in its transaction (``updateEstimateLine``,
US-1490/L3), and EP-09 extends it for the remaining to commit (``setLineRemaining``);
``revision_has_lines`` answers the designation of a reference, whether a revision bears a line
(``register_tasks_and_lines``, ``lines``, WF-CYC-0030); ``load_lines`` writes the lines of a
revision of the witness at the identifiers and the instant it imposes (US-1570).

Declared by US-1490/L1, unregistered: US-1490/L3 registers ``revision_has_lines`` once a line is
created, and adapts the tests of the designation then (decision of 2026-11-08, #2370). Each
raises ``NotImplementedError`` naming the story that fills it, and gives it its arguments.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def update_line(session: Session, project_id: UUID, node_id: UUID) -> None:
    """Change a line at the counter read, and price it again (``updateEstimateLine``)."""
    msg = "update_line is filled by US-1490/L3"
    raise NotImplementedError(msg)


def revision_has_lines(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears a line of estimate (WF-CYC-0030)."""
    msg = "revision_has_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def load_lines(session: Session, revision_id: UUID) -> None:
    """Write the lines of a revision of the witness, at the identifiers and the instant imposed."""
    msg = "load_lines is filled by US-1570"
    raise NotImplementedError(msg)
