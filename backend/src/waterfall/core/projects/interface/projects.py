# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project: read, listed, created, changed; its commands; what the journal names it by.

Created with its creator as project manager, its default work package and order item, the
transition to ``created`` and the partitions of its revised tables, in one transaction
(WF-PRJ-0010, WF-PRJ-0080, WF-DAT-0050); locked for any transition, any creation of a revision,
any designation, exit or write of the contributors (EP-04, "Modules"); its code and its label of the
day for the journal (#927); whether a background task that writes in its current revision is queued
or running, a condition of the commands that would write in it or freeze it.

Declared by US-0910/L1, without effect: US-0920/L1 fills the project, US-0920/L2 its names for the
journal, US-0970 the background task; ``load_project`` writes with the identifier and the instant
the witness imposes.
"""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The six states of the cycle of life, as the contract says them (``ProjectState``).
type ProjectState = Literal["created", "pricing", "in_progress", "completed", "lost", "abandoned"]


def read_project(session: Session, project_id: UUID) -> None:
    """Read a project, with its commands (``getProject``)."""


def list_projects(session: Session) -> None:
    """List the projects, filtered, sorted and read by pages (``listProjects``)."""


def create_project(session: Session, act: Act) -> None:
    """Create a project, and what is born with it (``createProject``)."""


def update_project(session: Session, project_id: UUID, lock_version: int, act: Act) -> None:
    """Change the attributes of a project at the version read (``updateProject``)."""


def lock_project(session: Session, project_id: UUID) -> None:
    """Lock the row of a project for the transaction, before it is read (``FOR UPDATE``)."""


def project_commands(session: Session, project_id: UUID) -> None:
    """Give the commands of a project and the conditions each lacks (WF-IHM-0090)."""


def project_label(session: Session, project_id: UUID) -> str | None:
    """Give the label of the day of a project, ``None`` if there is none (#927)."""


def project_code(session: Session, project_id: UUID) -> str | None:
    """Give the code of the day of a project, ``None`` if it has none (#927)."""


def no_background_task_running(session: Session, project_id: UUID) -> bool:
    """Tell whether no background task that writes in the project is queued or running.

    Always true until US-0970: no task of the platform aims at a project before the marking.
    """
    del session, project_id
    return True


def load_project(session: Session, project_id: UUID, act: Act) -> None:
    """Write a project of the witness, with the identifier and the instant it imposes."""
