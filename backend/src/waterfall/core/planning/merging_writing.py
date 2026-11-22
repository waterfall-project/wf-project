# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The main structure a merge writes, private to the module (WF-REV-0050, US-2560/L2).

The plan of the report (``merging``) is written as it presents it, under the lock of the project
and of the two structures, in the transaction of the merge. Three steps, in the order of the parts
of the merge, the estimate's between them — a line moves from a task that leaves before that task
goes:

1. ``write_tasks``: a task the differential adds enters the main structure under the lineage it
   has there, a new one to the main structure, its facet the differential's, bearing no attachment
   to the work breakdown (WF-PLA-0170); a task of both takes the columns the differential changes,
   and keeps its lineage, its state, its progress, its inscriptions and its attachment; a summary
   the merge leaves without a subordinate becomes a leaf in the state they gave it; every task the
   merge leaves is under its parent, at its place, the nodes whose place changes written; the links
   are the differential's: added, changed, removed;
2. ``place_lines``: the lines each task the merge leaves bears — those of the differential's task,
   in its order, a line of the main structure of the same lineage moved there, one it lacks created
   under the lineage of the differential's; a started task kept, its own lines; then the provision
   lines, which no differential holds, those of the task first, those of a task removed after,
   which go to the nearest ancestor that stays, or to the first task of the first level
   (WF-RIS-0010) —; the lines no task bears any more are deleted. The estimate writes the facets;
3. ``finish``: the tasks the differential removes and the merge does not keep are deleted, each
   started task kept is completed on the day of the merge, and the engine is replayed once on the
   main structure, which prices all its lines again on the dates it gives them.

The nodes of the differential are not written: it is read merged in the revision the merge marks.
"""

from dataclasses import dataclass, field
from itertools import count
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.planning.dating import conflicts_of
from waterfall.core.planning.merging import MergePlan, merge_plan, task_fields
from waterfall.core.planning.rebasing import COLUMNS, PARENT
from waterfall.core.planning.rescheduling import Holding, replayed
from waterfall.core.planning.shaping import PARKED, deleted, emptied, stamp
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import LINE, TASK, read_links, read_tree
from waterfall.core.planning.views import COMPLETED, STARTED, state_of
from waterfall.core.projects.interface import current_day
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from waterfall.core.planning.tree import NodeRow, TaskRow, Tree
    from waterfall.core.revisions.interface import StructureMerging

# Where what the writing of the tasks leaves is kept for the lines and the end of the merge.
WRITTEN = "planning.merge_written"


@dataclass(slots=True)
class Written:
    """What the writing of the tasks leaves: the node of each task merged, the links in conflict.

    ``nodes`` the node in the main structure of each task the plan names, its own for a task of
    the main structure, a new one for a task the differential adds; ``conflicts`` the links in
    conflict the main structure held before the merge wrote its links, each by its two tasks.
    """

    nodes: dict[UUID, UUID] = field(default_factory=dict[UUID, UUID])
    conflicts: frozenset[tuple[UUID, UUID]] = frozenset()


def _written(merging: StructureMerging) -> Written:
    """Give what the writing of the tasks left, kept in the frame of the merge."""
    held = merging.shared.get(WRITTEN)
    if not isinstance(held, Written):
        msg = "the lines and the end of a merge are written after its tasks"
        raise TypeError(msg)
    return held


def _new_node(merging: StructureMerging, source: NodeRow, kind: str) -> Node:
    """Give the node a merge creates in the main structure, of the lineage of the differential's.

    At its first version, parked above any rank at the first level, its place to be set.
    """
    at, author = merging.act.at, merging.act.author
    return Node(
        project_id=merging.project_id,
        id=new_id(),
        revision_id=merging.revision_id,
        structure_id=merging.main_structure_id,
        lineage_id=source.lineage_id,
        kind=kind,
        parent_id=None,
        rank=PARKED,
        origin_risk_id=source.origin_risk_id,
        lock_version=1,
        created_at=at,
        created_by=author,
        updated_at=at,
        updated_by=author,
    )


def _new_task(merging: StructureMerging, plan: MergePlan, task_id: UUID, node_id: UUID) -> Task:
    """Give the facet of a task the differential adds, as the differential has it.

    It bears no attachment to the work breakdown: a differential bears none (WF-PLA-0170).
    """
    taken = plan.facet(task_id)
    return Task(
        project_id=merging.project_id,
        node_id=node_id,
        structure_id=merging.main_structure_id,
        kind=TASK,
        label=taken.label,
        description=taken.description,
        scheduling_mode=taken.scheduling_mode,
        duration_value=taken.duration_value,
        duration_unit=taken.duration_unit,
        start_date=taken.start_date,
        start_hours=taken.start_hours,
        finish_date=taken.finish_date,
        finish_hours=taken.finish_hours,
        progress=taken.progress,
        started_on=taken.started_on,
        completed_on=taken.completed_on,
        external_id=taken.external_id,
        order_item_id=None,
        work_package_id=None,
        total_float_days=taken.total_float_days,
        is_critical=taken.is_critical,
    )


def _ranked(
    groups: Iterable[tuple[UUID | None, list[UUID]]],
) -> dict[UUID, tuple[UUID | None, int]]:
    """Give the parent and the rank of each node of each group, from one, in their order."""
    return {
        node: (parent, rank)
        for parent, members in groups
        for rank, node in enumerate(members, start=1)
    }


def _arrange(
    merging: StructureMerging,
    tree: Tree,
    final: Mapping[UUID, tuple[UUID | None, int]],
    created: Mapping[UUID, Node],
    leaving: Iterable[UUID] = (),
) -> None:
    """Put the nodes in their places: the new ones parked, then those that move; stamp those.

    Every node whose place changes, and each that ``leaving`` names, is parked above any rank first,
    so that the rank stays unique under its parent and of its kind at each statement; then each
    takes its place. ``final`` the parent and the rank of each node placed.
    """
    session, act = merging.session, merging.act
    turn = count(PARKED + 1)
    for node in created.values():
        node.rank = next(turn)
        session.add(node)
    session.flush()
    moved = [
        each
        for each, place in final.items()
        if each in tree.nodes and (tree.nodes[each].parent_id, tree.nodes[each].rank) != place
    ]
    for each in [*leaving, *moved]:
        tree.nodes[each].rank = next(turn)
    session.flush()
    for each, (parent, rank) in final.items():
        node = created.get(each) or tree.nodes[each]
        node.parent_id, node.rank = parent, rank
    for each in moved:
        stamp(tree.nodes[each], act)
    session.flush()


def _carried(merging: StructureMerging, plan: MergePlan, tree: Tree) -> None:
    """Give each task of both the columns the differential changes, its parent apart.

    A summary the merge leaves without a subordinate is a leaf first, in the state they gave it
    (WF-PLA-0040). A task that changes no column is not written here.
    """
    for task_id in plan.order:
        if task_id not in plan.sources or task_id not in plan.main.nodes:
            continue
        if tree.is_summary(task_id) and not plan.is_summary(task_id):
            emptied(tree, task_id)
            stamp(tree.nodes[task_id], merging.act)
        names = [name for name in task_fields(plan, task_id) if name != PARENT]
        if not names:
            continue
        task, taken = tree.tasks[task_id], plan.facet(task_id)
        for name in names:
            for column in COLUMNS[name]:
                setattr(task, column, getattr(taken, column))
        stamp(tree.nodes[task_id], merging.act)
    merging.session.flush()


def _linked(
    merging: StructureMerging, plan: MergePlan, tree: Tree, nodes: Mapping[UUID, UUID]
) -> None:
    """Write the links of the differential into the main structure: added, changed, removed.

    The task a link is written to — its successor — is counted, as an entry of its predecessors
    counts it; a task that leaves is not.
    """
    session, act = merging.session, merging.act
    held = {
        (each.predecessor_id, each.successor_id): each
        for each in read_links(session, merging.project_id, merging.main_structure_id)
    }
    wanted = {(nodes[before], nodes[after]): row for (before, after), row in plan.links.items()}
    counted: set[UUID] = set()
    for pair, link in held.items():
        row = wanted.get(pair)
        if row is None:
            session.delete(link)
            counted.add(pair[1])
        elif (link.link_type, link.lag_value, link.lag_unit) != (
            row.link_type,
            row.lag_value,
            row.lag_unit,
        ):
            link.link_type, link.lag_value, link.lag_unit = (
                row.link_type,
                row.lag_value,
                row.lag_unit,
            )
            counted.add(pair[1])
    session.flush()
    for pair, row in wanted.items():
        if pair in held:
            continue
        session.add(
            TaskLink(
                project_id=merging.project_id,
                id=new_id(),
                revision_id=merging.revision_id,
                structure_id=merging.main_structure_id,
                predecessor_id=pair[0],
                successor_id=pair[1],
                link_type=row.link_type,
                lag_value=row.lag_value,
                lag_unit=row.lag_unit,
                in_conflict=False,
            )
        )
        counted.add(pair[1])
    leaving = set(plan.removed)
    for each in counted:
        if each in tree.nodes and each not in leaving:
            stamp(tree.nodes[each], act)
    session.flush()


def write_tasks(merging: StructureMerging) -> None:
    """Write the tasks and the links of a merge into the main structure; those removed stay.

    The tree is read under the lock of the structure, which the merge holds.
    """
    plan = merge_plan(merging)
    session, project_id = merging.session, merging.project_id
    tree = read_tree(session, project_id, merging.main_structure_id)
    conflicts = conflicts_of(read_links(session, project_id, merging.main_structure_id))
    created = {
        task_id: _new_node(merging, plan.amendment.nodes[plan.sources[task_id]], TASK)
        for task_id in plan.order
        if task_id not in plan.main.nodes
    }
    nodes = {each: created[each].id if each in created else each for each in plan.order}
    merging.shared[WRITTEN] = Written(nodes, conflicts)
    _carried(merging, plan, tree)
    groups: dict[UUID | None, list[UUID]] = {}
    for task_id in plan.order:
        parent = plan.parents[task_id]
        groups.setdefault(None if parent is None else nodes[parent], []).append(nodes[task_id])
    final = _ranked(groups.items())
    _arrange(merging, tree, final, {node.id: node for node in created.values()}, plan.removed)
    session.add_all(_new_task(merging, plan, each, created[each].id) for each in created)
    session.flush()
    _linked(merging, plan, tree, nodes)


def _own_lines(tree: Tree[NodeRow, TaskRow]) -> dict[UUID, UUID]:
    """Give the node of each line of a tree besides the provisions, by its lineage."""
    return {
        node.lineage_id: each
        for each, node in tree.nodes.items()
        if node.kind == LINE and each not in tree.provisions
    }


def _lines_of(
    plan: MergePlan, task_id: UUID, lineages: tuple[Mapping[UUID, UUID], Mapping[UUID, UUID]]
) -> list[UUID]:
    """Give the lines a task merged bears, by their node in the main structure or the differential.

    A task of the differential, its own lines in its order — the main structure's node of the same
    lineage when there is one —; a task kept, its own lines the differential holds nowhere; then the
    provision lines of the task in the main structure. ``lineages`` the node of each own line, by
    its lineage: in the main structure, then in the differential (``_own_lines``).
    """
    main, amendment = plan.main, plan.amendment
    own, sent = lineages
    found: list[UUID] = []
    source = plan.sources.get(task_id)
    if source is not None:
        found += [
            own.get(amendment.nodes[each].lineage_id, each) for each in amendment.own_lines(source)
        ]
    else:
        found += [
            each for each in main.own_lines(task_id) if main.nodes[each].lineage_id not in sent
        ]
    if task_id in main.nodes:
        found += [each for each in main.lines(task_id) if each in main.provisions]
    return found


def place_lines(merging: StructureMerging) -> dict[UUID, UUID]:
    """Write the nodes of the lines a merge leaves in the main structure; give those it creates.

    By the node in the differential of each line it creates, its node in the main structure; the
    lines no task bears any more are deleted, before the nodes that stay take their places.
    """
    plan, written = merge_plan(merging), _written(merging)
    session, project_id = merging.session, merging.project_id
    amendment = plan.amendment
    # Read once for every task, not task by task: on a structure of thousands of lines, each task
    # walking all the nodes made the merge of the witness's amendment quadratic.
    lineages = (_own_lines(plan.main), _own_lines(amendment))
    lists = {written.nodes[each]: _lines_of(plan, each, lineages) for each in plan.order}
    first = plan.order[0] if plan.order else None
    for task_id in plan.main.order:
        if task_id not in plan.removed:
            continue
        target = plan.staying(task_id) or first
        moving = [each for each in plan.main.lines(task_id) if each in plan.main.provisions]
        if target is not None and moving:
            lists[written.nodes[target]] += moving
    placed = {each for members in lists.values() for each in members}
    tree = read_tree(session, project_id, merging.main_structure_id)
    gone = [each for each in tree.nodes if tree.nodes[each].kind == LINE and each not in placed]
    if gone:
        deleted(session, project_id, tree, gone)
        tree = read_tree(session, project_id, merging.main_structure_id)
    created = {
        each: _new_node(merging, amendment.nodes[each], LINE)
        for members in lists.values()
        for each in members
        if each in amendment.nodes
    }
    final = _ranked(
        (task, [created[each].id if each in created else each for each in members])
        for task, members in lists.items()
    )
    _arrange(merging, tree, final, {node.id: node for node in created.values()})
    return {each: node.id for each, node in created.items()}


def finish(merging: StructureMerging) -> None:
    """Delete the tasks the merge removes, complete the started ones it keeps, replay the engine.

    A started task kept is completed on the day of the merge, its start kept (WF-REV-0050): its
    lines' remaining to commit the estimate brought to nought. The engine is replayed once on the
    main structure, which prices all its lines again on the dates of their tasks.
    """
    plan, written = merge_plan(merging), _written(merging)
    session, project_id, act = merging.session, merging.project_id, merging.act
    tree = read_tree(session, project_id, merging.main_structure_id)
    if plan.removed:
        deleted(session, project_id, tree, list(plan.removed))
        tree = read_tree(session, project_id, merging.main_structure_id)
    day = current_day(act.at)
    for task_id in plan.kept:
        if plan.is_summary(task_id) or state_of(plan.main, task_id).progress != STARTED:
            continue
        task = tree.tasks[task_id]
        task.progress, task.completed_on = COMPLETED, day
        stamp(tree.nodes[task_id], act)
    session.flush()
    repriced = tuple(written.nodes[each] for each in plan.order)
    held = Holding(conflicts=written.conflicts, repriced=repriced)
    replayed(session, project_id, merging.main_structure_id, act.at, held)
