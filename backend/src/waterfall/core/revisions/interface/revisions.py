# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of a project: the history, a revision read, created, abandoned; the partitions.

The partitions of the revised tables are created in the transaction of the creation of the project,
by the function of the owner of the tables (``create_project_partitions``, WF-DAT-0050): the role
of the service may execute it, and holds no other right of DDL. A revision is created by the copy
of the last marked one, ``copy_revision(session, source, target)``, which each epic extends table by
table (EP-06 the tasks, EP-07 the lines, EP-08 the structures); abandoned, with its rows deleted. A
write in a revision is refused once it is marked (``revision_draft``, 409).

Declared by US-0910/L1, which fills the partitions; the rest without effect, until US-0960 fills
it; ``load_revision`` writes a revision of the witness with the identifier and the instant it
imposes.
"""

from typing import TYPE_CHECKING, Literal

from sqlalchemy import func, select

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The two statuses of a revision, as the contract says them (``RevisionStatus``).
type RevisionStatus = Literal["draft", "marked"]


def create_project_partitions(session: Session, project_id: UUID) -> None:
    """Create the partitions of a project in each revised table, in the transaction of ``session``.

    A project that has them already is refused by the database, which raises.
    """
    session.execute(select(func.create_project_partitions(project_id)))


def current_revision(session: Session, project_id: UUID) -> UUID | None:
    """Give the current revision of a project, ``None`` if it has none (WF-REV-0010)."""


def list_revisions(session: Session, project_id: UUID) -> None:
    """List the revisions of a project, its history (``listRevisions``, WF-REV-0070)."""


def read_revision(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Read a revision, with its commands (``getRevision``)."""


def create_revision(session: Session, project_id: UUID, act: Act) -> None:
    """Open the current revision of a project, a copy of its last marked (``createRevision``)."""


def copy_revision(session: Session, source: UUID, target: UUID) -> None:
    """Copy what a marked revision holds into a new one: its structures, here."""


def abandon_revision(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Abandon the current revision of a project, its rows deleted (``abandonRevision``)."""


def revision_draft(session: Session, revision_id: UUID) -> None:
    """Refuse a write in a revision that is not the current one (409, ``revision_draft``)."""


def load_revision(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Open a revision of the witness, with the identifier and the instant it imposes."""
