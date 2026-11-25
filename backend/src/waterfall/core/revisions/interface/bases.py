# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential: found, kept apart, and the state of its differential carried over.

The base of a differential is the copy of the main structure it was taken from (EP-08, "La base
d'un différentiel et sa mise à jour"): created with its differential (``create_differential``),
deleted with it (``abandon_structure``), taken up with it by the copy of a revision
(``copy_structures``) — all in ``structures``. This module gives what the other modules ask of it:
the base of a differential, which its reading compares it to (``differential_base``), and the
differential of a base, by which a refusal that concerns a task of the base names the task of the
differential (``base_differential``, #4213); the conditions that a column of structures names no
base (``not_a_base``), which what counts the nodes or the lines of a revision or of a project leaves
out, the structures but the bases across the projects (``structures_but_bases``), and only
structures that hold their lineages alone (``holds_its_lineages``), which a reading by lineage
reads; whether a structure is read against its base (``read_against_base``), a
differential or the own estimate of a risk whole (EP-30); whether a differential is up to date
(``differential_up_to_date``), which the loader of the witness asks before a merge (US-2560/L2);
and, at the end of the copy of a revision, the state of each differential it took up, up to date or
out of date, as it was in the revision marked (``keep_differential_states``).

Written by US-3050/L2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.revisions.interface.shared import MAIN, bears_main_counter, main_counter
from waterfall.core.revisions.interface.structures import AMENDMENT, BASE, RISK
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import ColumnElement, SQLColumnExpression, Subquery
    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface.revisions import RevisionCopy
    from waterfall.core.revisions.interface.structures import StructureFacts


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


def base_differential(session: Session, project_id: UUID, structure_id: UUID) -> UUID | None:
    """Give the differential a base was taken for; ``None`` for a structure that is no base."""
    return session.scalar(
        select(CostStructure.differential_id).where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind == BASE,
        )
    )


def not_a_base(
    structure: SQLColumnExpression[UUID],
    project: UUID | SQLColumnExpression[UUID],
    revision: UUID | SQLColumnExpression[UUID] | None = None,
) -> ColumnElement[bool]:
    """Say of a column of structures that it names no base of a differential (US-3050).

    For the tables of the planning, which hold the column and do not name this table: what counts
    the nodes or the lines of a project — of a revision, ``revision`` given — leaves the bases out,
    in the statement that counts. ``project`` and ``revision``, a value or the column of the row.
    """
    criteria = [CostStructure.project_id == project, CostStructure.kind == BASE]
    if revision is not None:
        criteria.append(CostStructure.revision_id == revision)
    return structure.not_in(select(CostStructure.id).where(*criteria))


def structures_but_bases() -> Subquery:
    """Give every structure of every project but the bases of the differentials, as a subquery.

    Its columns ``project_id`` and ``structure_id``: what a question across the projects joins to
    the nodes it reads, where ``not_a_base`` correlated to the project of each node would be judged
    again for every one (US-3070/L3b).
    """
    return (
        select(CostStructure.project_id.label("project_id"), CostStructure.id.label("structure_id"))
        .where(CostStructure.kind != BASE)
        .subquery()
    )


def holds_its_lineages(
    structure: SQLColumnExpression[UUID], project: UUID, revision: UUID
) -> ColumnElement[bool]:
    """Say of a column of structures that it is one of a revision that holds its lineages alone.

    The main structure alone: a differential, the own estimate of a risk and their bases copy the
    main structure under its lineages (US-3050, EP-30), and a reading by lineage reads none of them.
    """
    return structure.in_(
        select(CostStructure.id).where(
            CostStructure.project_id == project,
            CostStructure.revision_id == revision,
            CostStructure.kind == MAIN,
        )
    )


def read_against_base(session: Session, project_id: UUID, facts: StructureFacts) -> bool:
    """Tell whether a structure is read against its base: a differential, or a whole own estimate.

    The own estimate of a risk is read so while it is whole, with its base, as a differential is
    (EP-30, "La recomposition, la mise à jour et l'élagage"); one that has no base — consumed and
    taken up empty by the next revision — is read as it is.
    """
    if facts.is_differential:
        return True
    return (
        facts.is_own_estimate
        and differential_base(session, project_id, facts.structure_id) is not None
    )


def differential_up_to_date(session: Session, project_id: UUID, structure_id: UUID) -> bool:
    """Tell whether a differential is up to date; false for a structure that is no differential.

    Up to date while the main structure of its revision bears the counter its base was taken at
    (US-3050).
    """
    row = session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind == AMENDMENT,
        )
    ).first()
    if row is None:
        return False
    return bears_main_counter(row, main_counter(session, project_id, row.revision_id))


def keep_differential_states(copy: RevisionCopy) -> None:
    """Give each differential, and own estimate, the copy took up the state it had in the source.

    Called once every table is copied, the main structure of the copy redated: a differential up
    to date in the revision marked bears the counter of the main structure of the copy, and is up
    to date in it; one out of date keeps ``NEVER_BORNE``, which the main structure never bears
    (``FIRST_VERSION`` and after), and stays out of date until its update (WF-REV-0100, US-3050).
    The own estimate of a risk keeps its state alike (EP-30, "Les états d'un devis propre").
    """
    source_counter = main_counter(copy.session, copy.project_id, copy.source)
    up_to_date = copy.session.scalars(
        select(CostStructure.id).where(
            CostStructure.project_id == copy.project_id,
            CostStructure.revision_id == copy.source,
            CostStructure.kind.in_((AMENDMENT, RISK)),
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
        .values(main_lock_version=main_counter(copy.session, copy.project_id, copy.target))
        .execution_options(synchronize_session=False)
    )
