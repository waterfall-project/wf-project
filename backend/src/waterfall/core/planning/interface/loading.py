# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the witness: a revision's tree reconciled with the one the witness describes.

``load_tasks`` is what the loader of the witness asks of the planning for a revision it has just
opened (EP-06, "Le chargeur du témoin"): the structure of the revision holds what the copy gave it,
and the witness says what it must hold. The two are reconciled by lineage, the structure locked:

- a task the copy gave and the witness does not describe is deleted, with its subtree;
- a task both hold, under the identifier the witness imposes, is changed in place;
- a task both hold under another identifier — the copy draws its own — is deleted and written
  again at the identifier imposed, its lineage kept;
- a task only the witness describes is created, at its identifier and under its lineage.

The links are then replaced by those described, the planning start of the structure written, the
engine replayed on the whole structure — the dates are those it computes — and the states laid, a
leaf at a time (``load_progress``). The reconciliation gives back the tasks whose computed dates
are not the ones described. Every row bears the act that is given, whose instant the witness
imposes (``Act.at``).

A file of its own: ``nodes`` holds the reading and the writes of the tree, and a source file stops
at a thousand lines.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, insert

from waterfall.core.planning.interface.progress import ProgressLoad, load_progress
from waterfall.core.planning.rescheduling import replayed
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.shaping import deleted
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK, read_tree
from waterfall.core.planning.views import NOT_STARTED
from waterfall.core.planning.writing import facts_of, judge_revision
from waterfall.core.revisions.interface import write_structure

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.planning.scheduling import Duration
    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import Place
    from waterfall.platform.audit import Act

# The rank a task kept is moved to while the ranks are laid again: no sibling holds it.
_ASIDE = 1_000_000
_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/task_link")


@dataclass(frozen=True, slots=True)
class LinkLoad:
    """A link the witness describes, by the lineage of its predecessor."""

    predecessor_lineage_id: UUID
    link_type: str
    lag_value: Decimal
    lag_unit: str


@dataclass(frozen=True, slots=True)
class TaskLoad:
    """A task as the witness describes it: its identifiers, its place, its facet, its state.

    ``position`` orders the siblings; the dates ``start`` and ``finish`` are those the witness
    expects, which an automatic task is placed at by the engine and a manual one keeps.
    """

    node_id: UUID
    lineage_id: UUID
    parent_lineage_id: UUID | None
    position: int
    label: str
    description: str | None
    scheduling_mode: str
    duration: Duration
    start: WorkInstant
    finish: WorkInstant
    work_package_id: UUID | None
    order_item_id: UUID | None
    links: tuple[LinkLoad, ...]
    progress: str
    started_on: date | None
    completed_on: date | None


@dataclass(frozen=True, slots=True)
class TasksLoad:
    """What the witness describes of a structure: its planning start, its tasks parents first."""

    planning_start_on: date
    tasks: tuple[TaskLoad, ...]


@dataclass(frozen=True, slots=True)
class DatesDisagreeing:
    """A task whose dates the engine computed other than the witness describes them."""

    lineage_id: UUID
    label: str
    described: tuple[WorkInstant, WorkInstant]
    computed: tuple[WorkInstant, WorkInstant]


def _stale(tree: Tree, described: dict[UUID, TaskLoad]) -> list[UUID]:
    """Name the tasks the copy gave that the witness does not hold as described, subtrees too."""
    stale: set[UUID] = set()
    for node_id in tree.order:
        node = tree.nodes[node_id]
        if node.kind != TASK:
            continue
        found = described.get(node.lineage_id)
        if found is None or found.node_id != node_id or node.parent_id in stale:
            stale.add(node_id)
    return [each for each in tree.order if each in stale]


def _ranks(tasks: tuple[TaskLoad, ...]) -> dict[UUID, int]:
    """Give the rank of each task among its siblings, by lineage: the order of their positions."""
    siblings: dict[UUID | None, list[TaskLoad]] = {}
    for task in tasks:
        siblings.setdefault(task.parent_lineage_id, []).append(task)
    return {
        task.lineage_id: rank
        for found in siblings.values()
        for rank, task in enumerate(sorted(found, key=lambda each: each.position), start=1)
    }


def _stamp(act: Act) -> dict[str, object]:
    """Give the audit columns of a row written by the act."""
    return {
        "created_at": act.at,
        "created_by": act.author,
        "updated_at": act.at,
        "updated_by": act.author,
    }


def _reconciled(session: Session, place: Place, load: TasksLoad, act: Act) -> None:
    """Delete, change and create the tasks of the structure so that it holds those described."""
    project_id = place.project_id
    described = {each.lineage_id: each for each in load.tasks}
    tree = read_tree(session, project_id, place.structure_id)
    stale = _stale(tree, described)
    if stale:
        deleted(session, project_id, tree, stale)
        session.flush()
    gone = set(stale)
    held = {node_id for node_id, node in tree.nodes.items() if node.kind == TASK} - gone
    for node_id in held:
        tree.nodes[node_id].rank += _ASIDE
    session.flush()
    nodes = {each.lineage_id: each.node_id for each in load.tasks}
    ranks = _ranks(load.tasks)
    created: list[dict[str, object]] = []
    task_rows: list[dict[str, object]] = []
    for each in load.tasks:
        parent = None if each.parent_lineage_id is None else nodes[each.parent_lineage_id]
        facet = {
            "label": each.label,
            "description": each.description,
            "scheduling_mode": each.scheduling_mode,
            "duration_value": each.duration.value,
            "duration_unit": each.duration.unit,
            "start_date": each.start.day,
            "start_hours": each.start.hours,
            "finish_date": each.finish.day,
            "finish_hours": each.finish.hours,
            "progress": NOT_STARTED,
            "started_on": None,
            "completed_on": None,
            "order_item_id": each.order_item_id,
            "work_package_id": each.work_package_id,
        }
        if each.node_id in held:
            node = tree.nodes[each.node_id]
            node.parent_id, node.rank = parent, ranks[each.lineage_id]
            node.lock_version += 1
            node.updated_at, node.updated_by = act.at, act.author
            for column, value in facet.items():
                setattr(tree.tasks[each.node_id], column, value)
            continue
        created.append(
            {
                "project_id": project_id,
                "id": each.node_id,
                "revision_id": place.revision_id,
                "structure_id": place.structure_id,
                "lineage_id": each.lineage_id,
                "kind": TASK,
                "parent_id": parent,
                "rank": ranks[each.lineage_id],
                "origin_risk_id": None,
                "lock_version": 1,
                **_stamp(act),
            }
        )
        task_rows.append(
            {
                "project_id": project_id,
                "node_id": each.node_id,
                "structure_id": place.structure_id,
                "kind": TASK,
                **facet,
                "total_float_days": None,
                "is_critical": False,
            }
        )
    # The created are inserted before the changes of the kept are flushed: a kept task moved under
    # a created one would otherwise be written before its parent exists.
    if created:
        with session.no_autoflush:
            session.execute(insert(Node), created)
            session.execute(insert(Task), task_rows)
    session.flush()


def _linked(session: Session, place: Place, load: TasksLoad) -> None:
    """Replace the links of the structure by those described, at identifiers derived from them."""
    session.execute(
        delete(TaskLink)
        .where(TaskLink.project_id == place.project_id, TaskLink.structure_id == place.structure_id)
        .execution_options(synchronize_session=False)
    )
    nodes = {each.lineage_id: each.node_id for each in load.tasks}
    rows = [
        {
            "project_id": place.project_id,
            "id": uuid5(_LINK_NAMESPACE, f"{each.node_id}/{nodes[link.predecessor_lineage_id]}"),
            "revision_id": place.revision_id,
            "structure_id": place.structure_id,
            "predecessor_id": nodes[link.predecessor_lineage_id],
            "successor_id": each.node_id,
            "link_type": link.link_type,
            "lag_value": link.lag_value,
            "lag_unit": link.lag_unit,
            "in_conflict": False,
        }
        for each in load.tasks
        for link in each.links
    ]
    if rows:
        session.execute(insert(TaskLink), rows)


def _disagreeing(session: Session, place: Place, load: TasksLoad) -> tuple[DatesDisagreeing, ...]:
    """Name the tasks whose dates, as computed and kept, are not the ones described."""
    tree = read_tree(session, place.project_id, place.structure_id)
    found: list[DatesDisagreeing] = []
    for each in load.tasks:
        task = tree.tasks[each.node_id]
        computed = (
            WorkInstant(task.start_date, task.start_hours),
            WorkInstant(task.finish_date, task.finish_hours),
        )
        if computed != (each.start, each.finish):
            found.append(
                DatesDisagreeing(each.lineage_id, each.label, (each.start, each.finish), computed)
            )
    return tuple(found)


def load_tasks(
    session: Session, place: Place, load: TasksLoad, act: Act
) -> tuple[DatesDisagreeing, ...]:
    """Reconcile the structure of a revision just opened with the tasks the witness describes.

    The structure is judged as any write of its tree is (a revision still a draft), then locked.
    The tasks, the links and the planning start are written, the engine replayed once, and the
    states laid on the leaves that are not at the start (``load_progress``, so that a summary,
    whose state is derived, is never written). Gives the tasks whose computed dates are not the
    ones described, none when the engine and the witness agree.
    """
    judge_revision(session, place.project_id, place.revision_id)
    facts_of(session, place, lock=True)
    _reconciled(session, place, load, act)
    _linked(session, place, load)
    write_structure(
        session, place.project_id, place.structure_id, (load.planning_start_on, None), act
    )
    replayed(session, place.project_id, place.structure_id, act.at)
    summaries = {each.parent_lineage_id for each in load.tasks}
    for each in load.tasks:
        if each.lineage_id in summaries:
            continue
        if (each.progress, each.started_on, each.completed_on) != (NOT_STARTED, None, None):
            state = ProgressLoad(each.node_id, each.progress, each.started_on, each.completed_on)
            load_progress(session, place.project_id, state, act)
    return _disagreeing(session, place, load)
