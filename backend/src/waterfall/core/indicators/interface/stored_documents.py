# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A document a marked revision kept, read as it was kept (WF-DAT-0040; US-1670/L1).

What the readings of a marked revision answer: those of EP-10, and those of the indicators of the
estimate (EP-07) and of the remaining to commit (EP-09), which keep their computation for the
current revision (EP-10, "La conservation au marquage"; US-1670/L2). None for a kind and a scope the
marking did not keep: the indicators of the project, for a revision marked before In progress; a
subproject created after the marking.

Declared by US-1660/L1, the socle of EP-10; filled by US-1670/L1, which keeps the documents.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import case, select

from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import marked_revisions_at, revision_project
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document, IndicatorKind


def stored_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, scope: CostScope
) -> Document | None:
    """Give the document of a kind and a scope a revision kept at its marking, or none.

    The table is partitioned by project: the project of the revision is read first and named in the
    filter, so that only its partition is probed (404 for a revision that does not exist).
    """
    project_id = revision_project(session, revision_id)
    return session.scalar(
        select(RevisionIndicator.document).where(
            RevisionIndicator.project_id == project_id,
            RevisionIndicator.revision_id == revision_id,
            RevisionIndicator.kind == kind,
            RevisionIndicator.scope == str(scope),
        )
    )


@dataclass(frozen=True, slots=True)
class KeptOfKind:
    """What a revision kept of a kind for a scope: the document, and whether it kept the kind."""

    document: Document | None
    kind_kept: bool


def kept_of_kind(
    session: Session, revision_id: UUID, kind: IndicatorKind, scope: CostScope
) -> KeptOfKind:
    """Give the document of a kind and a scope a revision kept, and whether it kept the kind.

    One statement, after the project of the revision: the row of the scope if the marking kept
    it, else one of another scope. A revision that kept the kind but not a scope does not know that
    scope (a subproject created since its marking); one that kept none of the kind was marked
    before the indicators were kept (#3613).
    """
    project_id = revision_project(session, revision_id)
    asked = RevisionIndicator.scope == str(scope)
    row = session.execute(
        select(case((asked, RevisionIndicator.document), else_=None))
        .where(
            RevisionIndicator.project_id == project_id,
            RevisionIndicator.revision_id == revision_id,
            RevisionIndicator.kind == kind,
        )
        .order_by(asked.desc())
        .limit(1)
    ).first()
    if row is None:
        return KeptOfKind(None, kind_kept=False)
    return KeptOfKind(row[0], kind_kept=True)


def revisions_keeping_project(session: Session, project_id: UUID) -> set[UUID]:
    """Give the revisions of a project that kept the indicators of the project, in one statement."""
    return set(
        session.scalars(
            select(RevisionIndicator.revision_id).where(
                RevisionIndicator.project_id == project_id,
                RevisionIndicator.kind == "project",
                RevisionIndicator.scope == str(PROJECT),
            )
        )
    )


def kept_revision(
    session: Session, project_id: UUID, revision_id: UUID | None, as_of: date | None
) -> UUID:
    """Give the marked revision a reading of a marking reads: the one named, or the one of a date.

    The one named is read as it is; ``as_of`` names the last revision marked on or before that day
    — the day of the time zone of the installation — among those that kept the indicators of the
    project, the 409 ``STATE_FORBIDS_OPERATION``, without a state, when none did (EP-10, "Le calcul
    des indicateurs").
    """
    if revision_id is not None:
        return revision_id
    kept = kept_revisions(session, project_id)
    for found, marked_at in reversed(kept):
        if as_of is None or current_day(marked_at) <= as_of:
            return found
    raise ConflictError(STATE_FORBIDS_OPERATION)


def kept_revisions(session: Session, project_id: UUID) -> list[tuple[UUID, datetime]]:
    """Give the marked revisions of a project that kept its indicators, by marking, earliest first.

    Those that kept a document ``project`` for the project as a whole: marked In progress. Two
    markings of one instant are ordered by identifier.
    """
    marked = marked_revisions_at(session, project_id)
    keeping = revisions_keeping_project(session, project_id)
    return [
        (each, marked[each])
        for each in sorted(marked, key=lambda each: (marked[each], each))
        if each in keeping
    ]
