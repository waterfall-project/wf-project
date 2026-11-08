# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cost structures of a revision: its main one here (WF-REV-0100), and their commands.

The main structure is created with the first revision of a project, and is its only one; a
revision created from a marked one takes up its structures but the merged ones (``is_merged``: an
amendment consumed by its merge, the own estimate of a risk that occurred), each under an
identifier of its own and the lineage of the one it copies (WF-DAT-0030, #1759). The amendments
and the risks' own come with EP-08, which adds their kinds.

The date a structure's planning starts on is the day of its first creation by default, which a
copy keeps (``CostStructure.planning_start_on``), and the instant its dates were computed is that
of its creation until EP-06 schedules it (``scheduled_at``): both are written at the creation and
taken up by the copy (#2170). A row the migration ``0023`` did not fill reads them as they were
derived before: the day of the creation of the origin of its lineage, which is always there — the
revision it was created in was marked, since a copy takes up only a marked revision's —, or, were
it missing, the day of its own creation rather than vanish from its list.

Filled by US-0960. The witness loads no structure of its own: the main one is born with its
revision, the others are EP-06's and EP-07's.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from waterfall.core.projects.interface import CommandAvailability, contributor_kind, project_facts
from waterfall.core.revisions.commands import structure_commands_of
from waterfall.core.revisions.interface.shared import NOT_FOUND
from waterfall.core.revisions.states import revision_state
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.errors import NotFoundError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.revisions.interface.revisions import RevisionCopy
    from waterfall.platform.audit import Act

MAIN = "main"
# The label of the main structure at its creation, as the examples of the contract name it.
MAIN_LABEL = "Structure principale"


@dataclass(frozen=True, slots=True)
class StructureView:
    """A cost structure as it is read: its attributes and its commands for the reader."""

    structure_id: UUID
    revision_id: UUID
    kind: str
    label: str
    planning_start_on: date
    is_merged: bool
    commands: tuple[CommandAvailability, ...]
    lock_version: int


def create_main_structure(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> UUID:
    """Create the main structure of the first revision of a project, its only one (WF-REV-0100)."""
    structure_id = new_id()
    session.add(
        CostStructure(
            project_id=project_id,
            id=structure_id,
            revision_id=revision_id,
            kind=MAIN,
            label=MAIN_LABEL,
            is_merged=False,
            lineage_id=structure_id,
            planning_start_on=act.at.date(),
            scheduled_at=act.at,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    session.flush()
    return structure_id


def copy_structures(copy: RevisionCopy) -> None:
    """Copy the structures of the source but the merged ones, each keeping its lineage (#1759).

    Each keeps the date its planning starts on and the instant its dates were computed (#2170): a
    null date stays null, read by the lineage the copy keeps; a null instant is the creation of the
    structure copied.
    """
    rows = copy.session.scalars(
        select(CostStructure)
        .where(
            CostStructure.project_id == copy.project_id,
            CostStructure.revision_id == copy.source,
            CostStructure.is_merged.is_(False),
        )
        .order_by(CostStructure.id)
    ).all()
    for row in rows:
        copied = new_id()
        copy.identifiers[row.id] = copied
        copy.session.add(
            CostStructure(
                project_id=copy.project_id,
                id=copied,
                revision_id=copy.target,
                kind=row.kind,
                label=row.label,
                is_merged=False,
                lineage_id=row.lineage_id,
                planning_start_on=row.planning_start_on,
                scheduled_at=row.scheduled_at or row.created_at,
                created_at=copy.at,
                created_by=copy.author,
                updated_at=copy.at,
                updated_by=copy.author,
            )
        )
    copy.session.flush()


def delete_structures(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Delete the structures of a revision being abandoned, row by row (WF-DAT-0010)."""
    for row in session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id, CostStructure.revision_id == revision_id
        )
    ):
        session.delete(row)
    session.flush()


def _structures(
    session: Session, project_id: UUID, revision_id: UUID
) -> list[tuple[CostStructure, datetime]]:
    """Read the structures of a revision, the main one first, with the birth of their lineage.

    A structure whose lineage lost its origin is born with itself: it is listed all the same.
    """
    origin = aliased(CostStructure)
    rows = session.execute(
        select(CostStructure, func.coalesce(origin.created_at, CostStructure.created_at))
        .outerjoin(
            origin,
            (origin.project_id == CostStructure.project_id)
            & (origin.id == CostStructure.lineage_id),
        )
        .where(CostStructure.project_id == project_id, CostStructure.revision_id == revision_id)
        .order_by((CostStructure.kind != MAIN), CostStructure.label, CostStructure.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def list_cost_structures(
    session: Session, project_id: UUID, revision_id: UUID, viewer: Viewer
) -> list[StructureView]:
    """List the structures of a revision, with their commands (``listCostStructures``); or 404."""
    revision = revision_state(session, project_id, revision_id)
    state = project_facts(session, project_id).state
    kind = contributor_kind(session, project_id, viewer.user_id)
    return [
        StructureView(
            structure_id=row.id,
            revision_id=row.revision_id,
            kind=row.kind,
            label=row.label,
            planning_start_on=row.planning_start_on or born.date(),
            is_merged=row.is_merged,
            commands=tuple(
                CommandAvailability(command, missing)
                for command, missing in structure_commands_of(
                    viewer.permissions, kind, state, revision, main=row.kind == MAIN
                )
            ),
            lock_version=row.lock_version,
        )
        for row, born in _structures(session, project_id, revision_id)
    ]


def structure_commands(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID, viewer: Viewer
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a structure of a revision and the conditions each lacks; or 404."""
    for view in list_cost_structures(session, project_id, revision_id, viewer):
        if view.structure_id == structure_id:
            return view.commands
    raise NotFoundError(NOT_FOUND)
