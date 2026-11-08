# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of a task, by its lineage, to the timelines and to the time/time tracking.

``setNodeTracking`` replaces the inscriptions of a task, kept by its lineage so that they follow it
from revision to revision (WF-PLA-0060, WF-PLA-0140; EP-06, US-1400): the entries sent are the
inscriptions the task keeps afterwards, those it no longer names are deleted, an entry repeated
as it is making only one. It is written as the other fields of a task are, under the planning entry
command of the structure (``edit_planning``): the revision judged, the structure locked, the node
at the version read (412), then every entry judged at once (422), nothing being written if one is
refused:

- a ``milestone_tracking`` entry on a task that is no milestone: ``MILESTONE_REQUIRED``, on
  ``/entries/<n>/kind``; with a timeline, ``FIELD_NOT_ACCEPTED`` on ``/entries/<n>/timeline_id``;
- a ``timeline`` entry without a timeline: ``VALUE_REQUIRED``; with a timeline that is not one of
  the project: ``UNKNOWN_TIMELINE``, both on ``/entries/<n>/timeline_id``.

A timeline deleted between the judgement and the write is met by the key of the inscription, which
refuses it: the entries are judged again and refused as the unknown timeline they now name, never
as a failure. No lock is taken on the timelines read, the deletion of one holding the project
that the key of every inscription waits for. The node counts the write (its version advances), as
a field of the facet does; the history keeps it as a ``tracking`` change.

``load_tracking`` writes those of a task of the witness, by the rules of the write but the state.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.planning.tables import Timeline, TrackingEntry
from waterfall.core.planning.writing import NodesWritten, Place, Writer, writing
from waterfall.platform.errors import (
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
VALUE_REQUIRED = "VALUE_REQUIRED"
MILESTONE_REQUIRED = "MILESTONE_REQUIRED"
UNKNOWN_TIMELINE = "UNKNOWN_TIMELINE"
FIELD_NOT_ACCEPTED = "FIELD_NOT_ACCEPTED"
TIMELINE = "timeline"
MILESTONE_TRACKING = "milestone_tracking"


@dataclass(frozen=True, slots=True)
class TrackingSent:
    """An inscription as it is sent (``TrackingEntry``): its kind, and its timeline if sent."""

    kind: str
    timeline_id: UUID | None


@dataclass(frozen=True, slots=True)
class TrackingChange:
    """The inscriptions a task keeps, and the version of its node that was read."""

    entries: Sequence[TrackingSent]
    lock_version: int


@dataclass(frozen=True, slots=True)
class TrackingLoad:
    """The inscriptions the witness gives a task, by its lineage, and whether it is a milestone."""

    lineage_id: UUID
    entries: Sequence[TrackingSent]
    is_milestone: bool


def _known(session: Session, project_id: UUID, entries: Sequence[TrackingSent]) -> set[UUID]:
    """Read the timelines the entries name that belong to the project."""
    named = {each.timeline_id for each in entries if each.timeline_id is not None}
    if not named:
        return set()
    return set(
        session.scalars(
            select(Timeline.id).where(Timeline.project_id == project_id, Timeline.id.in_(named))
        )
    )


def _judge(
    session: Session, project_id: UUID, entries: Sequence[TrackingSent], *, is_milestone: bool
) -> None:
    """Refuse the entries the rules refuse, every fault of every entry at once (422)."""
    known = _known(session, project_id, entries)
    faults: list[FieldError] = []
    for rank, entry in enumerate(entries):
        where = f"/entries/{rank}"
        if entry.kind == MILESTONE_TRACKING:
            if not is_milestone:
                faults.append(FieldError(f"{where}/kind", MILESTONE_REQUIRED))
            if entry.timeline_id is not None:
                faults.append(FieldError(f"{where}/timeline_id", FIELD_NOT_ACCEPTED))
        elif entry.timeline_id is None:
            faults.append(FieldError(f"{where}/timeline_id", VALUE_REQUIRED))
        elif entry.timeline_id not in known:
            faults.append(FieldError(f"{where}/timeline_id", UNKNOWN_TIMELINE))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def _replace(
    session: Session, project_id: UUID, lineage_id: UUID, entries: Sequence[TrackingSent], act: Act
) -> None:
    """Make the inscriptions of a lineage the entries given: the others deleted, the new written.

    An inscription kept is left as it is, with its author and its instant; an entry repeated is
    written once.
    """
    wanted = list(dict.fromkeys((each.kind, each.timeline_id) for each in entries))
    held = {
        (row.kind, row.timeline_id): row
        for row in session.scalars(
            select(TrackingEntry).where(
                TrackingEntry.project_id == project_id, TrackingEntry.lineage_id == lineage_id
            )
        )
    }
    gone = [row.id for key, row in held.items() if key not in wanted]
    if gone:
        session.execute(delete(TrackingEntry).where(TrackingEntry.id.in_(gone)))
    for kind, timeline_id in wanted:
        if (kind, timeline_id) not in held:
            session.add(
                TrackingEntry(
                    id=new_id(),
                    project_id=project_id,
                    lineage_id=lineage_id,
                    kind=kind,
                    timeline_id=timeline_id,
                    created_at=act.at,
                    created_by=act.author,
                    updated_at=act.at,
                    updated_by=act.author,
                )
            )
    session.flush()


def _write(session: Session, project_id: UUID, load: TrackingLoad, act: Act) -> None:
    """Judge the entries, then replace the inscriptions of the lineage with them."""
    _judge(session, project_id, load.entries, is_milestone=load.is_milestone)
    try:
        with session.begin_nested():
            _replace(session, project_id, load.lineage_id, load.entries, act)
    except IntegrityError:
        # A timeline left between the judgement and the write: judged again, it is unknown.
        _judge(session, project_id, load.entries, is_milestone=load.is_milestone)
        raise


def set_node_tracking(
    session: Session,
    place: Place,
    node_id: UUID,
    change: TrackingChange,
    writer: Writer,
) -> NodesWritten:
    """Replace the inscriptions of a task, at the counter read (``setNodeTracking``).

    Under the lock of the structure: refused if the node is no task of it (404), at another
    version (412), or for an entry the rules refuse (422, every fault at once); nothing is then
    written. The task and its ancestors are given back as they now are, the version of the task
    one more.
    """
    with writing(session, place, writer, ("tracking", (node_id,))) as write:
        tree = write.tree
        if node_id not in tree.tasks:
            raise NotFoundError(NOT_FOUND)
        node = tree.nodes[node_id]
        if node.lock_version != change.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        write.before((node_id,))
        load = TrackingLoad(node.lineage_id, change.entries, tree.is_milestone(node_id))
        _write(session, place.project_id, load, writer.act)
        node.lock_version += 1
        node.updated_at = writer.act.at
        node.updated_by = writer.act.author
        redated = write.redate((node_id, tree.tasks[node_id].label))
        write.after((node_id,))
        return redated.written((node_id,))


def load_tracking(session: Session, project_id: UUID, load: TrackingLoad, act: Act) -> None:
    """Write the inscriptions of a task of the witness, by its lineage, at the instant imposed.

    The inscriptions of the lineage become the entries given, as a write replaces them, judged by
    the same rules: the timelines they name are those of the project the witness has loaded, and
    ``is_milestone`` what the description says of the task.
    """
    _write(session, project_id, load, act)
