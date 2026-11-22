# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the modules of this package share: the lock of a revision, its refusals, its inscription.

The opening, the abandonment and the marking of a revision each lock the revision, judge it, and
inscribe what they did in the journal; this module holds the one lock, the one refusal and the one
inscription, so that they cannot drift apart. It holds likewise the one rule by which a differential
or an own estimate is up to date (``bears_main_counter``), and the counter of the main structure it
is judged against (``main_counter``).

The current revision of a project is held, besides, before its project is locked (US-1500/L2,
``hold_current_revision``). A write that holds the lock of a project and then writes in its current
revision — the designation of a reference, which refreshes the budgeted amounts of its lines, and
the change of the rate of inflation of the project, which prices them again (EP-07, "Le calcul des
montants") — would take the two locks in the order the marking and the abandonment never take
them: they lock the revision, then the project. Such a write shares the lock of the current
revision first (``FOR SHARE``, which the guard of the revised tables, ``FOR KEY SHARE``, and the
writes of the tree, ``FOR SHARE``, both admit, and which a marking or an abandonment, ``FOR
UPDATE``, waits for), then locks the project: no two locks are ever awaited both ways.

The current revision is read before the project is locked, and read again under its lock. A
revision held by the first call is held again by the second at once (a share taken twice does not
wait). A revision opened between the two reads (``createRevision`` committed after the first read
found no current revision, or a current one marked or abandoned since) is shared only under the
lock of the project, which is the order the marking never takes: a ``markRevision`` that locked
that revision meanwhile waits for the project while this write waits for the revision, and
PostgreSQL aborts one of the two as a deadlock. The window is the time between two reads of one
transaction and needs an opening committed in it; it is not closed here, closing it would take a
refusal (a new code) the contract does not have.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import project_code, project_facts, project_label
from waterfall.core.revisions.tables import STRUCTURE_KINDS, CostStructure, Revision
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import (
    AuditObject,
    AuditProject,
    AuditRevision,
    Inscription,
    record,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    STATE_FORBIDS_OPERATION,
    ConflictError,
    NotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface.structures import StructureFacts
    from waterfall.platform.audit import Act, AuditAction


# The kind of the main structure of a revision (``StructureKind``), read by the modules of this
# package that cannot import ``structures``, which imports them (#4003); the kinds all derive from
# ``STRUCTURE_KINDS``, the list the table constrains, so that no declaration can drift (#4033).
MAIN, AMENDMENT, RISK, BASE = STRUCTURE_KINDS
# The key of the session telling that the writes of the main structure under way are those of a
# provision line (``provision_written``).
_PROVISION_WRITTEN = "waterfall.revisions.provision_written"


@contextmanager
def provision_written(session: Session) -> Generator[None]:
    """Tell the counters of the main structure that what is written is a provision line (EP-30).

    Each time the counter of the main structure advances within, the own estimates of the risks of
    its revision that were up to date retain the new counter, in the same statement's transaction:
    the provision line does not change the project the severity is computed on, and the update of a
    risk, which writes its provision again, would otherwise put every other out of date (EP-30, "La
    recomposition, la mise à jour et l'élagage"). Only the write of a provision line is so framed:
    the planning writes its node, the estimate its figures.
    """
    held = session.info.get(_PROVISION_WRITTEN, False)
    session.info[_PROVISION_WRITTEN] = True
    try:
        yield
    finally:
        session.info[_PROVISION_WRITTEN] = held


def writing_provision(session: Session) -> bool:
    """Tell whether what is written of the main structure now is a provision line."""
    return bool(session.info.get(_PROVISION_WRITTEN, False))


def bears_main_counter(row: CostStructure, counter: int | None) -> bool:
    """Tell whether a differential or an own estimate is up to date: the one rule, every reading's.

    Up to date while the main structure of its revision, whose counter is ``counter``, bears
    the counter it retained (``main_lock_version``; US-3050, EP-30).
    """
    return row.main_lock_version == counter


def main_counter(session: Session, project_id: UUID, revision_id: UUID) -> int | None:
    """Give the counter of the main structure of a revision."""
    return session.scalar(
        select(CostStructure.lock_version).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind == MAIN,
        )
    )


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


def inscribe_structure(
    session: Session,
    project_id: UUID,
    structure: StructureFacts,
    act: Act,
    merged: tuple[UUID, str] | None = None,
) -> None:
    """Inscribe the abandonment of a differential, or its merge: it, its revision, its project.

    ``merged`` the revision a merge marks and the name it marks it under (US-2560/L2): the merge
    is inscribed then (``structure_merge``), the abandonment otherwise, its revision unnamed.
    """
    code = project_code(session, project_id)
    label = project_label(session, project_id)
    named = None if label is None else AuditProject(project_id, code, label)
    revision = AuditRevision(*(merged or (structure.revision_id, None)))
    audited = AuditObject("cost_structure", structure.structure_id, structure.label, revision)
    actor = inscribed_actor(session, act.author)
    action: AuditAction = "structure_abandon" if merged is None else "structure_merge"
    record(session, Inscription(action, actor, audited, act.at, project=named))


def hold_current_revision(session: Session, project_id: UUID) -> UUID | None:
    """Share the lock of the current revision of a project; give it, ``None`` without one; or 404.

    Read again under the lock: a revision marked or abandoned meanwhile is current no more, and
    none is given.
    """
    current = project_facts(session, project_id).current_revision_id
    if current is None:
        return None
    return session.scalar(
        select(Revision.id)
        .where(
            Revision.project_id == project_id,
            Revision.id == current,
            Revision.status == "draft",
        )
        .with_for_update(read=True)
    )
