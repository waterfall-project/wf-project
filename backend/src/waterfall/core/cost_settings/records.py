# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the natures and the categories of cost share to read and to write their rows (private).

Never a deletion: an object of the reference is deactivated (WF-DAT-0080). The author of a write
is an account, or ``None`` for the platform (WF-DAT-0070); the moment is an argument, never read
here. Every write takes ``NATURES_LOCK`` first when it depends on the state of a nature, then the
rows it changes: always in that order, so that two writes never wait for each other.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.users.interface import Author, read_authors
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ALREADY_EXISTS = "ALREADY_EXISTS"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
# The key of the advisory lock of the rule that binds a nature and its categories: a category is
# never active under a nature that is not. Distinct from the other ones of the service.
NATURES_LOCK = 4_200_820


@dataclass(frozen=True, slots=True)
class Page:
    """Which objects of the order are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class Audit:
    """The columns of audit of a row, its authors named as they are shown, and its counter."""

    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None
    lock_version: int


def audits_of(session: Session, rows: Sequence[CostType | CostCategory]) -> list[Audit]:
    """Read the columns of audit of rows, each author named once, deactivated accounts too."""
    authors = read_authors(
        session,
        {user for row in rows for user in (row.created_by, row.updated_by) if user is not None},
    )
    return [
        Audit(
            row.created_at,
            None if row.created_by is None else authors.get(row.created_by),
            row.updated_at,
            None if row.updated_by is None else authors.get(row.updated_by),
            row.lock_version,
        )
        for row in rows
    ]


def lock_natures(session: Session) -> None:
    """Take the lock of the rule between a nature and its categories, until the transaction ends.

    By every write that reads the state of a nature to decide — a category created or moved under
    it, a reactivation, the cascade of a deactivation — before it reads anything.
    """
    session.execute(select(func.pg_advisory_xact_lock(NATURES_LOCK)))


def lock_row[Entity: (CostType, CostCategory)](
    session: Session, model: type[Entity], object_id: UUID, lock_version: int
) -> Entity:
    """Lock a row, then read it under the lock, at the version read; or refuse (404, 412)."""
    row = session.scalars(
        select(model)
        .where(model.id == object_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    if row.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": row.lock_version}
        )
    return row


def change_row[Entity: (CostType, CostCategory)](
    session: Session,
    model: type[Entity],
    object_id: UUID,
    values: Mapping[str, object],
    stamp: tuple[int, Act],
) -> Entity:
    """Change columns of a row whose version is the one read, and advance its version.

    The version is tested by the write itself: a write that finds another changes nothing and is
    refused (412). ``stamp`` is the version read and the act that writes.
    """
    lock_version, act = stamp
    changed = session.scalars(
        update(model)
        .where(model.id == object_id, model.lock_version == lock_version)
        .values(
            **values,
            lock_version=model.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .returning(model.id)
    ).first()
    if changed is None:
        current = session.scalars(select(model.lock_version).where(model.id == object_id)).first()
        if current is None:
            raise NotFoundError(NOT_FOUND)
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": current})
    return session.get_one(model, object_id, populate_existing=True)


def already_exists(fields: Collection[FieldError]) -> ConflictError:
    """Refuse values another object holds, each field named with the object that holds it (409)."""
    return ConflictError(ALREADY_EXISTS, fields=tuple(fields))


def value_taken(pointer: str, holder: UUID) -> FieldError:
    """Name a field whose value another object holds, and that object."""
    return FieldError(pointer, ALREADY_EXISTS, {"conflicting_object_id": str(holder)})


def identifier_taken(identifier: UUID) -> ConflictError:
    """Refuse an identifier the loader of the witness imposes and an object already bears (409)."""
    return ConflictError(ALREADY_EXISTS, {"conflicting_object_id": str(identifier)})
