# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates of a structure: the engine replayed on it, its start date and its label written.

``reschedule`` runs the engine (``scheduling``, pure) on a whole structure under its lock, writes
the dates and the floats that change and moves ``scheduled_at`` on (EP-06, "Modules"): every write
of a node does the same through its frame (``writing``, US-1380/L2), which names the task it wrote
when the horizon is crossed, and the task whose predecessors it enters when a loop is refused;
``reschedule`` serves a write that names none — the constants of the units, a calendar
(``reference``, US-1390/L2). Its body is private (``rescheduling``), which the frame calls too.

``update_cost_structure`` writes the date the planning of a structure starts on and its label
(``updateCostStructure``, #2170; US-1390/L2), under the frame of every write of the planning: its
revision judged — the command ``edit_planning`` (409) —, its entry of the history opened
(``structure_update``), the structure locked, its counter judged (412). The date is judged on the
default calendar, the structure having none of its own: a day without an hour of work is refused,
naming the next working day (``NON_WORKING_DAY``, WF-PLA-0010, WF-PLA-0020). The engine is then
replayed: a task in automatic mode without a predecessor starts at the new date, its automatic
successors follow, a task in manual mode keeps its dates (WF-PLA-0020); beyond fifteen years the
write is refused naming the task that finishes last (WF-PLA-0150). It writes no node: the tasks it
redates are given back (``rescheduled``), and the summaries above them (``ancestors``). The
snapshot the history keeps is the structure's own — its start and its label —, since no node is
written (``RecordedChange.node_ids`` empty); the structure after is built from what the write
holds, read once under the lock (#2492), at the counter of its redating, not read again.

``open_differential`` opens a differential, the copy of the main structure of a revision
(``createCostStructure``, US-2550/L3), and its base, a second copy (US-3050/L2);
``load_differential`` the same for the loader of the witness, under the identifiers it imposes on
the differential and on the copies of its nodes, its base drawn (US-2650/L1).

Declared by US-1380/L1; ``reschedule`` filled by US-1380/L2, handed what a write already holds by
US-1380/L3, ``update_cost_structure`` filled by US-1390/L2, its structure after built by US-1380/L5.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from waterfall.core.history.interface import ObjectState
from waterfall.core.planning.calendars import default_calendar
from waterfall.core.planning.interface.copying import copy_structure_nodes
from waterfall.core.planning.rescheduling import Holding, replayed
from waterfall.core.planning.writing import Place, facts_of, judge_revision, writing
from waterfall.core.revisions.interface import (
    CopyImposed,
    DifferentialName,
    RevisionCopy,
    aimed_structure,
    create_differential,
    write_structure,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue
    from waterfall.core.planning.rescheduling import Rescheduled
    from waterfall.core.planning.writing import NodesWritten, Writer
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.audit import Act

NON_WORKING_DAY = "NON_WORKING_DAY"


def reschedule(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    at: datetime,
    held: Holding | None = None,
) -> Rescheduled:
    """Replay the engine on a structure locked, write what changes; give what it moved.

    The structure is locked, its dates' instant moved on to ``at`` and its counter advanced; a
    write of the tree that holds the lock already hands what it read (``held``, #2492). Beyond
    fifteen years (WF-PLA-0150), refused (422 ``PROJECT_HORIZON_EXCEEDED``), nothing written:
    naming the task ``held`` blames or, without one, the task that finishes last.
    """
    return replayed(session, project_id, structure_id, at, held)


@dataclass(frozen=True, slots=True)
class StructureChange:
    """What a write of a structure sends: its start, its label — each ``None`` when not sent."""

    planning_start_on: date | None
    label: str | None
    lock_version: int


def structure_state(facts: StructureFacts) -> ObjectState:
    """Give the structure as the history keeps it: its start and its label, at its version.

    The object of an entry of ``structure_update``, which restores it (``restoring``).
    """
    structure: dict[str, JsonValue] = {
        "planning_start_on": facts.planning_start_on.isoformat(),
        "label": facts.label,
    }
    rows: dict[str, JsonValue] = {"structure": structure}
    return ObjectState(facts.structure_id, facts.lock_version, facts.label, rows)


def _judge_start(session: Session, day: date) -> None:
    """Refuse a start on a day the default calendar grants no hour, the next one named (422)."""
    calendar = default_calendar(session).calendar
    if calendar.hours_on(day) > 0:
        return
    try:
        following = calendar.next_working_day(day).isoformat()
    except ValueError:
        following = None
    params = {"date": day.isoformat(), "next_working_day": following}
    fault = FieldError("/planning_start_on", NON_WORKING_DAY, params)
    raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))


def update_cost_structure(
    session: Session, place: Place, change: StructureChange, writer: Writer
) -> NodesWritten:
    """Write the start date and the label of a structure at the counter read, and redate it.

    Refused at another version (412), on a day without hours of the default calendar or beyond
    the horizon (422); nothing is written then.
    """
    with writing(session, place, writer, ("structure_update", ())) as write:
        facts = write.facts
        if facts.lock_version != change.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": facts.lock_version}
            )
        if change.planning_start_on is not None:
            _judge_start(session, change.planning_start_on)
        write.frame.keep_before((structure_state(facts),))
        sent = (change.planning_start_on, change.label)
        write_structure(session, place.project_id, place.structure_id, sent, writer.act)
        # The replay is handed the facts as written: the new start, not the one read (#2492).
        written = replace(
            facts,
            planning_start_on=change.planning_start_on or facts.planning_start_on,
            label=facts.label if change.label is None else change.label,
        )
        write.facts = written
        redated = write.redate(None)
        # The structure after is the one written, at the instant and the counter of its redating:
        # built from what the write holds, not read again under the lock (#2492, #2513).
        after = replace(written, scheduled_at=writer.act.at, lock_version=redated.counter)
        write.frame.keep_after((structure_state(after),))
        return redated.written(())


def open_differential(
    session: Session, revision: tuple[UUID, UUID], label: str, writer: Writer
) -> UUID:
    """Open a differential in a revision: a structure that is the copy of the main one; give it.

    Refused on a marked revision (409 ``revision_draft``), a terminal project
    (``project_not_terminal``) and while a background task writes in the project
    (``no_background_task_running``), in that order, under the lock of the revision read
    ``FOR SHARE`` (``judge_revision``); nothing is written then. The main structure is locked, as a
    write of its nodes does, and copied whole under the lock: its start date, its dates as
    computed, its tasks and links, its lines at the figures they hold, each node under an
    identifier of its own and the lineage it has in the main structure, so that the differential
    is read against the main structure by that lineage, every node ``unchanged`` (WF-REV-0100,
    WF-REV-0050, C-361). Its tasks bear no attachment to the work breakdown, the main structure's
    alone (WF-PLA-0170). Not an entry of the history: nothing of a differential opened is undone,
    it is abandoned (``deleteCostStructure``). Its base is copied likewise under the same lock, the
    main structure as the differential copied it, which the differential is read against and which
    no operation serves (US-3050).
    """
    return _opened(session, revision, label, writer.act, None)


@dataclass(frozen=True, slots=True)
class DifferentialLoad:
    """A differential of the witness: its identifier and label, those of the copies of its nodes.

    ``nodes`` the identifier of the copy of a node of the main structure, by its lineage; a node
    not named is drawn, as the base and its nodes are (US-2650/L1).
    """

    structure_id: UUID
    label: str
    nodes: Mapping[UUID, UUID]


def load_differential(
    session: Session, revision: tuple[UUID, UUID], load: DifferentialLoad, act: Act
) -> None:
    """Open a differential of the witness as ``open_differential`` does, under its identifiers."""
    _opened(session, revision, load.label, act, load)


def _opened(
    session: Session,
    revision: tuple[UUID, UUID],
    label: str,
    act: Act,
    load: DifferentialLoad | None,
) -> UUID:
    """Open a differential and its base under the lock of the main structure; give it.

    ``load`` the identifiers the witness imposes, none for the service.
    """
    project_id, revision_id = revision
    # A revision of another project is unknown before it is judged: it has no main structure here.
    main_id = aimed_structure(session, project_id, revision_id, None)
    if main_id is None:
        raise NotFoundError(NOT_FOUND)
    judge_revision(session, project_id, revision_id)
    main = facts_of(session, Place(project_id, revision_id, main_id), lock=True)
    imposed = None if load is None else load.structure_id
    opened = create_differential(session, revision, main, DifferentialName(label, imposed), act)
    for target in (opened.structure_id, opened.base_id):
        nodes = {} if load is None or target != imposed else {target: load.nodes}
        copy = RevisionCopy(
            session,
            project_id,
            revision_id,
            revision_id,
            act.at,
            act.author,
            {main_id: target},
            within_revision=True,
            imposed=CopyImposed(nodes=nodes),
        )
        copy_structure_nodes(copy)
    return opened.structure_id
