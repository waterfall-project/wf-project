# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of the rates of a revision, as the revision judges and counts it (WF-REV-0060).

The rates a revision keeps are the estimate's (EP-07): this module knows neither them nor their
proposal. It asks the estimate whether the proposal of a revision presents a category
(``register_rate_update``), the condition ``rate_update_available`` of the command
``apply_rate_update`` (#1351), and frames the update the estimate writes (``update_rates``): the
revision locked and read under its lock, as its marking and its abandonment take it, at the counter
read (412), then the first condition the command lacks, in the order of the contract —
``revision_draft``, ``rate_update_available``, ``no_background_task_running`` (409) —; the estimate
writes the rates and prices the lines again, refusing what it does not accept (422); the revision
advances by one version, stamped by the update.

Written by US-1500/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.projects.interface import no_background_task_running
from waterfall.core.revisions.commands import RevisionState, revision_conditions
from waterfall.core.revisions.interface.shared import STALE_LOCK_VERSION, found_revision, refuse
from waterfall.core.revisions.registry import Registry
from waterfall.platform.errors import PreconditionFailedError

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# Whether the proposal of a revision presents a category: the estimate's, registered at the import
# of its interface, which this module never imports.
_PROPOSALS: Registry[Callable[[Session, UUID], bool]] = Registry("revisions.rate_update")


@dataclass(frozen=True, slots=True)
class RevisionRating:
    """What a revision tells the proposal of its rates: whether it is current, and its year."""

    project_id: UUID
    revision_id: UUID
    draft: bool
    reference_year: int


@dataclass(frozen=True, slots=True)
class RatesToUpdate:
    """The revision an update of the rates names, and the counter its caller read."""

    revision_id: UUID
    lock_version: int


def register_rate_update(question: Callable[[Session, UUID], bool]) -> Callable[[], None]:
    """Add the question whether the proposal of a revision presents a category; give its withdrawal.

    The estimate registers it (US-1500): without it, no revision has an update to apply.
    """
    return _PROPOSALS.register(question)


def rate_update_available(session: Session, revision_id: UUID) -> bool:
    """Tell whether the proposal of the rates of a revision presents a category (#1351)."""
    return any(question(session, revision_id) for question in _PROPOSALS.entries())


def revision_rating(session: Session, project_id: UUID, revision_id: UUID) -> RevisionRating:
    """Read whether a revision of a project is current, and its year of reference; or 404."""
    revision = found_revision(session, revision_id, project_id, lock=False)
    return RevisionRating(
        project_id, revision_id, revision.status == "draft", revision.reference_year
    )


def update_rates(
    session: Session,
    project_id: UUID,
    update: RatesToUpdate,
    act: Act,
    write: Callable[[RevisionRating], None],
) -> None:
    """Frame the update of the rates of a revision: judged, written by ``write``, then counted.

    Under the lock of the revision, read under it: unknown (404), at another version (412), then
    the first condition ``apply_rate_update`` lacks (409). ``write`` writes the rates and prices
    the lines again, or refuses (422), nothing being written; the revision advances by one version.
    """
    revision = found_revision(session, update.revision_id, project_id, lock=True)
    if revision.lock_version != update.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": revision.lock_version}
        )
    draft = revision.status == "draft"
    state = RevisionState(
        marked=not draft,
        no_task_running=no_background_task_running(session, project_id),
        has_tasks_and_lines=False,
        reference_correctable=False,
        rate_update_available=draft and rate_update_available(session, revision.id),
    )
    lacking = revision_conditions("apply_rate_update", state)
    if lacking:
        raise refuse(lacking[0])
    write(RevisionRating(project_id, revision.id, draft, revision.reference_year))
    revision.lock_version += 1
    revision.updated_at, revision.updated_by = act.at, act.author
    session.flush()
