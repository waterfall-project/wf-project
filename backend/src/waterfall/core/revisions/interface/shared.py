# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the modules of this package share: the lock of a revision, its refusals, its inscription.

The opening, the abandonment and the marking of a revision each lock the revision, judge it, and
inscribe what they did in the journal; this module holds the one lock, the one refusal and the one
inscription, so that they cannot drift apart.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import project_code, project_label
from waterfall.core.revisions.tables import Revision
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, Inscription, record
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act, AuditAction

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"


def refuse(condition: str) -> ConflictError:
    """Refuse an operation a condition forbids (409 ``STATE_FORBIDS_OPERATION``)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})


def found_revision(
    session: Session, revision_id: UUID, project_id: UUID | None = None, *, lock: bool
) -> Revision:
    """Read a revision, of a project if one is named; or refuse (404).

    ``lock`` reads it under the lock, taken ``FOR UPDATE``, not the ``FOR NO KEY UPDATE`` of an
    ``UPDATE`` alone: it excludes the ``FOR KEY SHARE`` under which the guard of a revised table
    reads the revision (#2104). The marking and the abandonment both take it.
    """
    query = select(Revision).where(Revision.id == revision_id)
    if project_id is not None:
        query = query.where(Revision.project_id == project_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    revision = session.scalars(query).first()
    if revision is None:
        raise NotFoundError(NOT_FOUND)
    return revision


def inscribe_revision(
    session: Session, revision: Revision, action: AuditAction, name: str | None, act: Act
) -> None:
    """Inscribe in the journal what was done to a revision: it, by its name, and its project."""
    code = project_code(session, revision.project_id)
    label = project_label(session, revision.project_id)
    # The journal names a project by its label, and by its code once it has one (#927, #2166).
    named = None if label is None else AuditProject(revision.project_id, code, label)
    audited = AuditObject("revision", revision.id, name)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription(action, actor, audited, act.at, project=named))
