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
successors and their summaries at this step, before the lines are loaded (``estimate_lines``, which
follows); the loader notes how many (``witness.tasks_dated_before_the_lines``: a count of this step,
not of the loaded witness, where none differs) and keeps the engine's. The identifier
of a node is its own in a revision: the file gives each lineage the one it has in the revision in
progress, where the examples of the contract read them; a marked revision holds the same lineages
under identifiers derived from those, so that two loadings give the same ones.

The file is read by a model of its own, strict, which does not import ``wftools``; the inscriptions
follow the lineage of each task from revision to revision (US-1400/L2): those a revision describes
replace the ones its lineage held.
"""

from datetime import date
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
from waterfall.core.planning.scheduling import Duration
from waterfall.core.revisions.interface import aimed_structure
from waterfall.platform.logs import get_logger
from waterfall.witness.filling import Strict, TaskRow, node_identifier

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.filling import Filling

TASKS_FILE = "witness_tasks.json"
_NODE_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/node")

logger = get_logger(__name__)


class _Revision(Strict):
    """What the description says of a revision: the day it is read at, its planning start."""

    revision: int
    read_on: date
    planning_start_on: date
    task_count: int


class _Tasks(Strict):
    """The tasks of the witness by revision, as ``witness_tasks.json`` keeps them."""

    revisions: list[_Revision]
    tasks: list[TaskRow]


def _load(task: TaskRow, node_id: UUID) -> TaskLoad:
    """Give a task as the planning loads it, under the identifier it has in its structure."""
    return TaskLoad(
        node_id=node_id,
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


def fill(session: Session, witness: Witness, filling: Filling) -> None:
    """Write the tasks the witness describes for a structure, by lineage.

    The tasks of the structure the copy gave are reconciled with the described ones, then, in a
    main structure, the inscriptions of each lineage written (the timelines are those of the slice
    before the revisions). A revision the file does not describe is left as it is.
    """
    number = filling.number
    described = witness.read(TASKS_FILE, _Tasks)
    revision = next((each for each in described.revisions if each.revision == number), None)
    if revision is None:
        return
    current = max(each.revision for each in described.revisions)
    tasks = filling.tasks(task for task in described.tasks if task.revision == number)
    project_id = filling.revision.project_id.root
    revision_id = filling.revision.revision_id.root
    changes = filling.changes
    structure_id = filling.structure_id or aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        message = f"revision {number} holds no main structure"
        raise ValueError(message)

    def identified(task: TaskRow) -> UUID:
        if changes is not None:
            return changes.node(task.lineage_id)
        return node_identifier(_NODE_NAMESPACE, task.revision, task.node_id, current)

    place = Place(project_id, revision_id, structure_id)
    written = (revision.planning_start_on, tasks)
    disagreeing = write_tasks(session, place, written, identified, filling.act)
    # The calendar of a task comes from the roles of its lines, which are loaded after the tasks
    # (``estimate_lines``): at this step the engine dates on the default calendar the tasks the 4x10
    # calendars of the file reach, with their successors and their summaries. The computed is kept,
    # and the count noted for this step alone: the lines then date them as the file does.
    kind = "main" if changes is None else "amendment"
    logger.info(
        "witness.tasks_dated_before_the_lines", revision=number, structure=kind, tasks=disagreeing
    )
    if changes is None:
        inscribe(session, project_id, tasks, filling.act)


def write_tasks(
    session: Session,
    place: Place,
    written: tuple[date, Iterable[TaskRow]],
    identified: Callable[[TaskRow], UUID],
    act: Act,
) -> int:
    """Reconcile a structure with the tasks described and its planning start; count the misdated.

    Those the engine dated otherwise than described are counted; ``identified`` gives the node of
    each task in the structure.
    """
    start, tasks = written
    load = TasksLoad(start, tuple(_load(task, identified(task)) for task in tasks))
    return len(load_tasks(session, place, load, act))


def inscribe(session: Session, project_id: UUID, tasks: Iterable[TaskRow], act: Act) -> None:
    """Write the inscriptions of each task described, by its lineage."""
    for task in tasks:
        entries = tuple(TrackingSent(each.kind, each.timeline_id) for each in task.inscriptions)
        tracking = TrackingLoad(task.lineage_id, entries, task.is_milestone)
        load_tracking(session, project_id, tracking, act)
