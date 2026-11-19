# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential: found, kept apart, and the state of its differential carried over.

The base of a differential is the copy of the main structure it was taken from (EP-08, "La base
d'un différentiel et sa mise à jour"): created with its differential (``create_differential``),
deleted with it (``abandon_structure``), taken up with it by the copy of a revision
(``copy_structures``) — all in ``structures``. This module gives what the other modules ask of it:
the base of a differential, which its reading compares it to (``differential_base``); the bases of
a revision, which what counts the structures of a revision leaves out (``revision_bases``); and,
at the end of the copy of a revision, the state of each differential it took up, up to date or out
of date, as it was in the revision marked (``keep_differential_states``).

Written by US-3050/L2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.revisions.interface.shared import MAIN
from waterfall.core.revisions.interface.structures import AMENDMENT, BASE
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface.revisions import RevisionCopy


def differential_base(session: Session, project_id: UUID, structure_id: UUID) -> UUID | None:
    """Give the base of a differential, in its revision; ``None`` for a structure that has none.

    A differential merged keeps its base in the revision its merge marks: it is read against it
    there (WF-REV-0100).
    """
    return session.scalar(
        select(CostStructure.id).where(
            CostStructure.project_id == project_id,
            CostStructure.differential_id == structure_id,
            CostStructure.kind == BASE,
        )
    )


def revision_bases(session: Session, project_id: UUID, revision_id: UUID) -> frozenset[UUID]:
    """Give the bases of the differentials of a revision, which nothing that counts it counts."""
    return frozenset(
        session.scalars(
            select(CostStructure.id).where(
                CostStructure.project_id == project_id,
                CostStructure.revision_id == revision_id,
                CostStructure.kind == BASE,
            )
        )
    )


def _main_counter(session: Session, project_id: UUID, revision_id: UUID) -> int | None:
    """Give the counter of the main structure of a revision."""
    return session.scalar(
        select(CostStructure.lock_version).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind == MAIN,
        )
    )


def keep_differential_states(copy: RevisionCopy) -> None:
    """Give each differential the copy of a revision took up the state it had in the source.

    Called once every table is copied, the main structure of the copy redated: a differential up
    to date in the revision marked bears the counter of the main structure of the copy, and is up
    to date in it; one out of date keeps 0, which the main structure never bears (``FIRST_VERSION``
    and after), and stays out of date until its update (WF-REV-0100, US-3050).
    """
    source_counter = _main_counter(copy.session, copy.project_id, copy.source)
    up_to_date = copy.session.scalars(
        select(CostStructure.id).where(
            CostStructure.project_id == copy.project_id,
            CostStructure.revision_id == copy.source,
            CostStructure.kind == AMENDMENT,
            CostStructure.is_merged.is_(False),
            CostStructure.main_lock_version == source_counter,
        )
    ).all()
    copies = [copy.identifiers[each] for each in up_to_date if each in copy.identifiers]
    if not copies:
        return
    copy.session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == copy.project_id, CostStructure.id.in_(copies))
        .values(main_lock_version=_main_counter(copy.session, copy.project_id, copy.target))
        .execution_options(synchronize_session=False)
    )
