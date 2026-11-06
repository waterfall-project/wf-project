# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of a project: work packages, order items, deliverables (WF-PRJ-0020).

Read whole or filtered, written whole under its own counter; an element left out is deleted, or
marked deleted when a task of a marked revision bears it (EP-06).

Declared by US-0910/L1, without effect: US-0950 fills it; ``load_work_breakdown`` writes that of
the witness.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def read_work_breakdown(session: Session, project_id: UUID) -> None:
    """Read the work breakdown of a project, whole or filtered (``getWorkBreakdown``)."""
    msg = "read_work_breakdown is filled by US-0950"
    raise NotImplementedError(msg)


def set_work_breakdown(session: Session, project_id: UUID, lock_version: int, act: Act) -> None:
    """Write the whole work breakdown of a project at the version read (``setWorkBreakdown``)."""
    msg = "set_work_breakdown is filled by US-0950"
    raise NotImplementedError(msg)


def load_work_breakdown(session: Session, project_id: UUID, act: Act) -> None:
    """Write the work breakdown of a project of the witness, as it imposes it."""
    msg = "load_work_breakdown is filled by US-0950"
    raise NotImplementedError(msg)
