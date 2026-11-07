# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference revision of a project: its designation, and what it asks of the revision.

A marked revision is designated reference while the project has neither an actual cost (EP-09)
nor a revision marked since the last designation (``reference_correctable``, WF-REV-0040); it must
bear tasks and lines (``revision_has_tasks_and_lines``, WF-CYC-0030), a question this module asks
of those of the planning and of the estimate, which EP-06 and EP-07 register
(``register_tasks_and_lines``): always false until then.

The moment of the last designation is the moment the reference revision was last written: a marked
revision is written by its designation alone (the trigger of the base admits that, and its
counter and audit).

The designation locks the project, then reads and writes the revisions it names, all marked: the
marking and the abandonment lock a current revision, then the project, and never a marked
revision, so that no two locks are taken in opposite orders. It judges under the lock, in the
order of the contract: the revision unknown (404), the counter of the project read (412), a
terminal project (409 ``project_not_terminal``), then the first condition the command
``designate_reference`` lacks (409). It writes ``is_reference`` of the previous reference and of
the new one, the project, and ``reference_designate`` in the journal; the project moves to In
progress if its code is entered (``set_reference_revision``).
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import (
    lock_for_designation,
    no_background_task_running,
    set_reference_revision,
)
from waterfall.core.revisions.commands import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    RevisionState,
    revision_conditions,
)
from waterfall.core.revisions.interface.shared import (
    STALE_LOCK_VERSION,
    found_revision,
    inscribe_revision,
    refuse,
)
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import Revision
from waterfall.platform.errors import PreconditionFailedError

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The questions a revision answers to bear tasks and lines: EP-06 its tasks, EP-07 its lines.
_TASKS_AND_LINES: Registry[Callable[[Session, UUID], bool]] = Registry()


def reference_correctable(session: Session, project_id: UUID) -> bool:
    """Tell whether the reference of a project is still correctable (WF-REV-0040).

    It is while the project has none, or while no revision was marked since the last designation.
    The actual costs, which also close it, are EP-09's.
    """
    designated_at = session.scalar(
        select(Revision.updated_at).where(
            Revision.project_id == project_id, Revision.is_reference.is_(True)
        )
    )
    if designated_at is None:
        return True
    later = session.scalar(
        select(Revision.id)
        .where(
            Revision.project_id == project_id,
            Revision.status == "marked",
            Revision.marked_at > designated_at,
        )
        .limit(1)
    )
    return later is None


def _write(revision: Revision, *, reference: bool, act: Act) -> None:
    revision.is_reference = reference
    revision.updated_at = act.at
    revision.updated_by = act.author
    revision.lock_version += 1


def designate_reference(
    session: Session, project_id: UUID, revision_id: UUID, lock_version: int, act: Act
) -> None:
    """Designate a marked revision reference of its project (``designateReferenceRevision``).

    Judged under the lock of the project, at the counter read; nothing is written if refused.
    """
    project = lock_for_designation(session, project_id)
    target = found_revision(session, revision_id, project_id, lock=False)
    if project.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": project.lock_version}
        )
    if project.state in TERMINAL:
        raise refuse(PROJECT_NOT_TERMINAL)
    state = RevisionState(
        marked=target.status == "marked",
        no_task_running=no_background_task_running(session, project_id),
        has_tasks_and_lines=revision_has_tasks_and_lines(session, revision_id),
        reference_correctable=reference_correctable(session, project_id),
    )
    lacking = revision_conditions("designate_reference", state)
    if lacking:
        raise refuse(lacking[0])
    # Marked, both: nothing but their designation writes them, and no marking locks them.
    previous = session.scalars(
        select(Revision)
        .where(
            Revision.project_id == project_id,
            Revision.is_reference.is_(True),
            Revision.id != revision_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if previous is not None:
        _write(previous, reference=False, act=act)
        # The index admits one reference per project: the old one leaves before the new one comes.
        session.flush()
    revision = found_revision(session, revision_id, project_id, lock=True)
    _write(revision, reference=True, act=act)
    session.flush()
    set_reference_revision(session, project_id, revision_id, act)
    inscribe_revision(session, revision, "reference_designate", revision.version_name, act)


def register_tasks_and_lines(question: Callable[[Session, UUID], bool]) -> Callable[[], None]:
    """Add a question a revision must answer yes to bear tasks and lines; give its withdrawal."""
    return _TASKS_AND_LINES.register(question)


def revision_has_tasks_and_lines(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears tasks and lines of estimate: every question registered says so.

    None registered, the revision bears none: false until EP-06 and EP-07 register theirs.
    """
    questions = _TASKS_AND_LINES.entries()
    return bool(questions) and all(question(session, revision_id) for question in questions)
