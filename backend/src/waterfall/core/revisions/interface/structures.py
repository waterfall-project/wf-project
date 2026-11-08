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

What the planning asks of a structure (EP-06, "Modules"): its facts, read or under its lock
(``structure_facts``), which every write of its nodes takes, and the instant of its dates moved on
with its counter (``structure_rescheduled``), at each write that redates it (US-1380/L2); the
condition of the phase an entry lacks, by the rule its commands state
(``structure_phase_conditions``, US-1380/L4); its start and its label written
(``write_structure``, ``updateCostStructure``), and the structures of the current revisions,
their revisions read ``FOR SHARE`` (``current_structures``), which a change of the reference
redates (US-1390/L2).

Filled by US-0960. The witness loads no structure of its own: the main one is born with its
revision, the others are EP-06's and EP-07's.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.orm import aliased

from waterfall.core.projects.interface import (
    CommandAvailability,
    contributor_kind,
    current_day,
    project_facts,
)
from waterfall.core.revisions.commands import phase_conditions, structure_commands_of
from waterfall.core.revisions.interface.shared import NOT_FOUND
from waterfall.core.revisions.states import revision_state
from waterfall.core.revisions.tables import CostStructure, Revision
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
            planning_start_on=current_day(act.at),
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
    structure copied. The planning then redates, at the opening, those that hold a node, with the
    reference of the day (``redate_copy``, EP-06).
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


def aimed_structure(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID | None
) -> UUID | None:
    """Give the structure of a revision an import aims at: the one named, or the main one.

    ``None`` when the structure named is not one of the revision — unknown, of another revision or
    of another project —, which the opening of an import refuses (404, EP-06).
    """
    criteria = [CostStructure.project_id == project_id, CostStructure.revision_id == revision_id]
    if structure_id is None:
        criteria.append(CostStructure.kind == MAIN)
    else:
        criteria.append(CostStructure.id == structure_id)
    return session.scalar(select(CostStructure.id).where(*criteria))


def structure_in_revision(
    session: Session, project_id: UUID, structure_id: UUID, revision_id: UUID
) -> UUID | None:
    """Give the structure of a revision that is ``structure_id``, or the copy of its lineage.

    An import analysed on a structure of the last marked revision applies to the copy the current
    revision holds of it (WF-INTF-0090, EP-06); ``None`` when the revision holds none.
    """
    lineage = session.scalar(
        select(CostStructure.lineage_id).where(
            CostStructure.project_id == project_id, CostStructure.id == structure_id
        )
    )
    if lineage is None:
        return None
    return session.scalar(
        select(CostStructure.id).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.lineage_id == lineage,
        )
    )


def structure_commands(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID, viewer: Viewer
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a structure of a revision and the conditions each lacks; or 404."""
    for view in list_cost_structures(session, project_id, revision_id, viewer):
        if view.structure_id == structure_id:
            return view.commands
    raise NotFoundError(NOT_FOUND)


def structure_phase_conditions(command: str, state: str, *, main: bool) -> tuple[str, ...]:
    """Name the condition of the phase of the project an entry of a structure lacks, if any.

    The rule the commands of a structure state in advance (``structure_commands``), for an entry
    sent in spite of them: on the main structure, ``project_before_in_progress`` for the estimate
    and ``project_in_progress`` for the remaining to commit; nothing for the planning, nor on
    another structure (WF-DEV-0050, WF-RAE-0040; #2494). A terminal project is judged before.
    """
    return tuple(phase_conditions(command, state, main=main))


@dataclass(frozen=True, slots=True)
class StructureFacts:
    """What the planning reads of a structure: its revision, its kind, its start, its instant.

    ``planning_start_on`` and ``scheduled_at`` are derived as the list reads them when the
    migration left them null (#2170); ``lock_version`` is the counter of its writes.
    """

    structure_id: UUID
    revision_id: UUID
    is_main: bool
    planning_start_on: date
    scheduled_at: datetime
    lock_version: int
    label: str


def structure_facts(
    session: Session, project_id: UUID, structure_id: UUID, *, lock: bool
) -> StructureFacts:
    """Read a structure of a project; or refuse (404).

    ``lock`` takes it ``FOR UPDATE`` and reads it under the lock: every write of its nodes does,
    after the revision and the stack of the history (EP-06, "L'historique annulable").
    """
    query = select(CostStructure).where(
        CostStructure.project_id == project_id, CostStructure.id == structure_id
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = session.scalars(query).first()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    start, at = row.planning_start_on, row.scheduled_at or row.created_at
    if start is None:
        origin = session.scalar(
            select(CostStructure.created_at).where(
                CostStructure.project_id == project_id, CostStructure.id == row.lineage_id
            )
        )
        start = (origin or row.created_at).date()
    return StructureFacts(
        row.id, row.revision_id, row.kind == MAIN, start, at, row.lock_version, row.label
    )


def structure_rescheduled(
    session: Session, project_id: UUID, structure_id: UUID, at: datetime
) -> int:
    """Move the instant of the dates of a structure on to ``at``, advance its counter; give it.

    To be called under the lock of the structure (``structure_facts``), by a write that redates it.
    """
    counted = session.scalar(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id == structure_id)
        .values(scheduled_at=at, lock_version=CostStructure.lock_version + 1)
        .returning(CostStructure.lock_version)
        .execution_options(synchronize_session=False)
    )
    if counted is None:
        raise NotFoundError(NOT_FOUND)
    return counted


def write_structure(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    change: tuple[date | None, str | None],
    act: Act,
) -> None:
    """Write the start and the label of a structure, each when given (``updateCostStructure``).

    To be called under the lock of the structure (``structure_facts``); its counter advances with
    the redating that follows (``structure_rescheduled``), once per write.
    """
    planning_start_on, label = change
    values: dict[str, object] = {"updated_at": act.at, "updated_by": act.author}
    if planning_start_on is not None:
        values["planning_start_on"] = planning_start_on
    if label is not None:
        values["label"] = label
    session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id == structure_id)
        .values(**values)
        .execution_options(synchronize_session=False)
    )


@dataclass(frozen=True, slots=True)
class CurrentStructure:
    """A structure of a current revision: its project, its revision, itself."""

    project_id: UUID
    revision_id: UUID
    structure_id: UUID


def current_structures(session: Session, *, lock: bool) -> tuple[CurrentStructure, ...]:
    """Give the structures of the current revisions, in the order of (``project_id``, ``id``).

    ``lock`` reads their revisions ``FOR SHARE``: a revision marked or abandoned meanwhile is left
    out, and none is until the transaction ends — what a change of the reference takes before it
    locks each structure in this order to redate it (EP-06, "Ce que le cadrage décide").
    """
    query = (
        select(CostStructure.project_id, CostStructure.revision_id, CostStructure.id)
        .join(
            Revision,
            (Revision.project_id == CostStructure.project_id)
            & (Revision.id == CostStructure.revision_id),
        )
        .where(Revision.status == "draft")
        .order_by(CostStructure.project_id, CostStructure.id)
    )
    if lock:
        query = query.with_for_update(read=True, of=Revision)
    return tuple(CurrentStructure(*row) for row in session.execute(query))
