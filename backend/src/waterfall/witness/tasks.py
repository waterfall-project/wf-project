# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the revisions of the witness: the content of each revision, between its events.

Registered by ``register_revision_filler`` (``chronology``): after the slice of the revisions opens
a revision of PRJ-001 — 100, 101, 102 — and before the next event marks it, it reconciles by
lineage the tasks the copy gave the revision with those ``witness_tasks.json`` describes for it —
created, changed, deleted, their links, their states, the date the planning of the structure starts
on —, then writes their inscriptions, through the interface of the planning, at the identifiers and
the instant imposed (EP-06, "Le chargeur du témoin").

The dates are those the engine computes: the computed is the expected. The file's, which the
generator draws with the calendars the lines of EP-07 give some tasks, differ for those tasks, their
successors and their summaries until EP-07 loads the lines; the loader notes how many
(``witness.tasks_dated_by_the_engine``) and keeps the engine's. The identifier
of a node is its own in a revision: the file gives each lineage the one it has in the revision in
progress, where the examples of the contract read them; a marked revision holds the same lineages
under identifiers derived from those, so that two loadings give the same ones.

The file is read by a model of its own, strict, which does not import ``wftools``; the inscriptions
follow the lineage of each task from revision to revision (US-1400/L2): those a revision describes
replace the ones its lineage held.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from waterfall.core.planning.interface import (
    LinkLoad,
    Place,
    TaskLoad,
    TasksLoad,
    TrackingLoad,
    TrackingSent,
    WorkInstant,
    load_tasks,
    load_tracking,
)
from waterfall.core.planning.scheduling import Duration, DurationUnit, LagUnit
from waterfall.core.revisions.interface import aimed_structure
from waterfall.platform.logs import get_logger
from waterfall.witness.filling import Strict, node_identifier, number_of

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.revisions import OpenedRevision

TASKS_FILE = "witness_tasks.json"
_NODE_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/node")

logger = get_logger(__name__)


class _Duration(Strict):
    """A duration: a value and its unit."""

    value: Decimal
    unit: DurationUnit


class _Lag(Strict):
    """A lag: a value and its unit."""

    value: Decimal
    unit: LagUnit


class _Moment(Strict):
    """A start or a finish: a day and the hours of work elapsed that day."""

    date: date
    hours: Decimal


class _Link(Strict):
    """A link to a predecessor, by its lineage."""

    predecessor_lineage_id: UUID
    link_type: str
    lag: _Lag


class _Inscription(Strict):
    """An inscription of a task of the witness, as the description writes it."""

    kind: str
    timeline_id: UUID | None


class _Task(Strict):
    """A task of a revision, as the description writes it."""

    revision: int
    node_id: UUID
    lineage_id: UUID
    parent_lineage_id: UUID | None
    position: int
    label: str
    description: str | None
    is_summary: bool
    is_milestone: bool
    scheduling_mode: str
    duration: _Duration
    start: _Moment
    finish: _Moment
    order_item_id: UUID | None
    work_package_id: UUID | None
    predecessors: list[_Link]
    progress: str
    started_on: date | None
    completed_on: date | None
    inscriptions: list[_Inscription]


class _Revision(Strict):
    """What the description says of a revision: the day it is read at, its planning start."""

    revision: int
    read_on: date
    planning_start_on: date
    task_count: int


class _Tasks(Strict):
    """The tasks of the witness by revision, as ``witness_tasks.json`` keeps them."""

    revisions: list[_Revision]
    tasks: list[_Task]


def _load(task: _Task, current: int) -> TaskLoad:
    """Give a task as the planning loads it."""
    return TaskLoad(
        node_id=node_identifier(_NODE_NAMESPACE, task.revision, task.node_id, current),
        lineage_id=task.lineage_id,
        parent_lineage_id=task.parent_lineage_id,
        position=task.position,
        label=task.label,
        description=task.description,
        scheduling_mode=task.scheduling_mode,
        duration=Duration(task.duration.value, task.duration.unit),
        start=WorkInstant(task.start.date, task.start.hours),
        finish=WorkInstant(task.finish.date, task.finish.hours),
        work_package_id=task.work_package_id,
        order_item_id=task.order_item_id,
        links=tuple(
            LinkLoad(link.predecessor_lineage_id, link.link_type, link.lag.value, link.lag.unit)
            for link in task.predecessors
        ),
        progress=task.progress,
        started_on=task.started_on,
        completed_on=task.completed_on,
    )


def fill(session: Session, witness: Witness, opened: OpenedRevision) -> None:
    """Write the tasks the witness describes for a revision just opened, by lineage.

    The tasks of the structure the copy gave are reconciled with the described ones, then the
    inscriptions of each lineage written (the timelines are those of the slice before the
    revisions). A revision the file does not describe is left as it is.
    """
    number = number_of(opened.revision.revision_id.root)
    described = witness.read(TASKS_FILE, _Tasks)
    revision = next((each for each in described.revisions if each.revision == number), None)
    if revision is None:
        return
    current = max(each.revision for each in described.revisions)
    tasks = [task for task in described.tasks if task.revision == number]
    project_id = opened.revision.project_id.root
    revision_id = opened.revision.revision_id.root
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        message = f"revision {number} holds no main structure"
        raise ValueError(message)
    load = TasksLoad(revision.planning_start_on, tuple(_load(task, current) for task in tasks))
    disagreeing = load_tasks(
        session, Place(project_id, revision_id, structure_id), load, opened.act
    )
    # The calendar of a task comes from the roles of its lines, which EP-07 loads: until then the
    # engine dates on the default calendar the tasks the 4x10 calendars of the file reach, with
    # their successors and their summaries. The computed is kept, and the count noted.
    logger.info("witness.tasks_dated_by_the_engine", revision=number, tasks=len(disagreeing))
    for task in tasks:
        entries = tuple(TrackingSent(each.kind, each.timeline_id) for each in task.inscriptions)
        tracking = TrackingLoad(task.lineage_id, entries, task.is_milestone)
        load_tracking(session, project_id, tracking, opened.act)
