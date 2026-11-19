# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The differential an update writes, private to the module (US-3050/L4).

The plan of the report (``rebasing``) is written as it presents it, under the lock of the project
and of the three structures, in the transaction of the update, the nodes of the differential
keeping their identifier (WF-REV-0100). Three steps, in the order of the parts of the update, the
estimate's between them — a line moves from the task that leaves before that task goes:

1. ``write_tasks``: a task the main structure adds enters the differential under its lineage, its
   facet the main structure's, bearing no attachment to the work breakdown, which a differential
   never has (WF-PLA-0170); a column carried is taken; every task the update leaves is under its
   parent, at its place — the nodes whose place changes written, their counter advanced —; the
   links are the plan's: added, changed, removed. A node that is not written is left as it is, its
   counter too, so that an entry of the history that holds it is still undone (WF-IHM-0110);
2. ``write_lines``: the nodes of the lines, which the estimate writes the facets of — a line the
   main structure adds enters under its task, after the sibling that precedes it there; one that
   leaves goes first;
3. ``finish``: the tasks that leave are deleted, the base is replaced by a copy of the main
   structure, the differential is up to date, and the engine is replayed once on it, which prices
   its lines again.

Nothing of the main structure is written. The update enters no entry of the history, nor the
journal.
"""

from dataclasses import dataclass
from itertools import count
from typing import TYPE_CHECKING

from waterfall.core.planning.dating import conflicts_of
from waterfall.core.planning.interface.copying import copy_structure_nodes
from waterfall.core.planning.interface.differential_deletion import delete_structure_nodes
from waterfall.core.planning.rebasing import COLUMNS, PARENT
from waterfall.core.planning.rescheduling import Holding, replayed
from waterfall.core.planning.shaping import PARKED, deleted, stamp
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import LINE, TASK, read_links, read_tree
from waterfall.core.planning.writing import Place
from waterfall.core.revisions.interface import RevisionCopy, rebased_structure
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from waterfall.core.planning.rebasing import RebasePlan
    from waterfall.core.planning.tree import Tree
    from waterfall.core.revisions.interface import StructureRebasing


@dataclass(frozen=True, slots=True)
class LinesPlaced:
    """Where the lines of the differential stand once updated, by the lineage of each line.

    ``placed`` the task each line the differential holds ends under, by its lineage, none for a
    line that leaves; ``created`` the task each line the main structure adds enters under;
    ``by_main`` the lines of the differential whose place the main structure gives — it moved
    them —, the others staying where the differential has them; ``changed`` the lines whose facet
    the estimate rewrites, which are counted.
    """

    placed: Mapping[UUID, UUID | None]
    created: Mapping[UUID, UUID]
    by_main: frozenset[UUID]
    changed: frozenset[UUID]


def _numbered(parent: UUID | None, held: list[Node | None]) -> list[int]:
    """Give the ranks the nodes of a parent take, in their order, writing as few as it can.

    A node already under the parent keeps its rank while it follows that of the node before it;
    another takes the next one — a node that is new, one that comes from another parent, one an
    insertion before it leaves no room for. So the nodes the update has no need to move are not
    written, and an entry of the history that holds one is still undone (WF-IHM-0110).
    """
    ranks: list[int] = []
    last = 0
    for node in held:
        keeps = node is not None and node.parent_id == parent and node.rank > last
        last = node.rank if keeps and node is not None else last + 1
        ranks.append(last)
    return ranks


def _places(plan: RebasePlan, tree: Tree) -> dict[UUID, tuple[UUID | None, int]]:
    """Give the parent and the rank of each task the update leaves, by its node."""
    groups: dict[UUID | None, list[UUID]] = {}
    for lineage in plan.order:
        groups.setdefault(plan.parents[lineage], []).append(lineage)
    final: dict[UUID, tuple[UUID | None, int]] = {}
    for parent, members in groups.items():
        parent_node = None if parent is None else plan.nodes[parent]
        held = [tree.nodes.get(plan.nodes[each]) for each in members]
        for lineage, rank in zip(members, _numbered(parent_node, held), strict=True):
            final[plan.nodes[lineage]] = (parent_node, rank)
    return final


def _new_node(rebasing: StructureRebasing, node_id: UUID, lineage: UUID, kind: str) -> Node:
    """Give a node the update creates, at its first version, its place to be set."""
    at, author = rebasing.act.at, rebasing.act.author
    return Node(
        project_id=rebasing.project_id,
        id=node_id,
        revision_id=rebasing.revision_id,
        structure_id=rebasing.structure_id,
        lineage_id=lineage,
        kind=kind,
        parent_id=None,
        rank=PARKED,
        origin_risk_id=None,
        lock_version=1,
        created_at=at,
        created_by=author,
        updated_at=at,
        updated_by=author,
    )


def _new_task(rebasing: StructureRebasing, plan: RebasePlan, lineage: UUID) -> Task:
    """Give the facet of a task the main structure adds, as the main structure has it.

    It bears no attachment to the work breakdown: a differential bears none (WF-PLA-0170).
    """
    taken = plan.main.task(lineage)
    return Task(
        project_id=rebasing.project_id,
        node_id=plan.nodes[lineage],
        structure_id=rebasing.structure_id,
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


def _move(
    rebasing: StructureRebasing,
    tree: Tree,
    final: Mapping[UUID, tuple[UUID | None, int]],
    created: Mapping[UUID, Node],
    leaving: list[UUID],
) -> set[UUID]:
    """Put the nodes in their places: the new ones, then those that move, parked first; give those.

    Every node whose place changes is parked above any rank, and so is each that leaves, so that
    the rank stays unique under its parent at each statement; each then takes its rank, and the
    nodes that moved are counted. ``final`` the parent and the rank of each node placed.
    """
    session, act = rebasing.session, rebasing.act
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
    for each in leaving:
        tree.nodes[each].rank = next(turn)
    for each in moved:
        tree.nodes[each].parent_id, tree.nodes[each].rank = final[each][0], next(turn)
    session.flush()
    for each, (parent, rank) in final.items():
        node = created.get(each) or tree.nodes[each]
        node.parent_id, node.rank = parent, rank
    for each in moved:
        stamp(tree.nodes[each], act)
    session.flush()
    return set(moved)


def _carried(rebasing: StructureRebasing, plan: RebasePlan, tree: Tree) -> None:
    """Give each task of both the columns the main structure changes and the differential takes.

    A task that takes none — its parent, which ``_move`` writes, apart — is not written.
    """
    for lineage, names in plan.carried.items():
        if not names - {PARENT}:
            continue
        node_id = plan.nodes[lineage]
        task, taken = tree.tasks[node_id], plan.main.task(lineage)
        for name in names - {PARENT}:
            for column in COLUMNS[name]:
                setattr(task, column, getattr(taken, column))
        stamp(tree.nodes[node_id], rebasing.act)


def _linked(rebasing: StructureRebasing, plan: RebasePlan, tree: Tree) -> None:
    """Write the links the plan leaves: those it adds, those it changes, those that go.

    The task a link is written to — its successor — is counted, as an entry of its predecessors
    counts it.
    """
    session, act = rebasing.session, rebasing.act
    held = {
        (tree.nodes[each.predecessor_id].lineage_id, tree.nodes[each.successor_id].lineage_id): each
        for each in read_links(session, rebasing.project_id, rebasing.structure_id)
    }
    counted: set[UUID] = set()
    leaving = {plan.nodes[each] for each in plan.removed}
    for pair, link in held.items():
        if pair not in plan.links:
            session.delete(link)
            counted.add(link.successor_id)
            continue
        wanted = plan.links[pair]
        values = (wanted.link_type, wanted.lag_value, wanted.lag_unit)
        if (link.link_type, link.lag_value, link.lag_unit) != values:
            link.link_type, link.lag_value, link.lag_unit = values
            counted.add(link.successor_id)
    session.flush()
    for pair, wanted in plan.links.items():
        if pair in held:
            continue
        session.add(
            TaskLink(
                project_id=rebasing.project_id,
                id=new_id(),
                revision_id=rebasing.revision_id,
                structure_id=rebasing.structure_id,
                predecessor_id=plan.nodes[pair[0]],
                successor_id=plan.nodes[pair[1]],
                link_type=wanted.link_type,
                lag_value=wanted.lag_value,
                lag_unit=wanted.lag_unit,
                in_conflict=False,
            )
        )
        counted.add(plan.nodes[pair[1]])
    for each in counted:
        if each in tree.nodes and each not in leaving:
            stamp(tree.nodes[each], act)
    session.flush()


def write_tasks(rebasing: StructureRebasing, plan: RebasePlan) -> None:
    """Write the tasks and the links of the update; the tasks that leave stay until its end.

    The nodes: those of the differential keep theirs, a task the main structure adds takes a new
    one under its lineage (``RebasePlan.nodes``). The tree is read under the lock of the structure.
    """
    session, project_id = rebasing.session, rebasing.project_id
    tree = read_tree(session, project_id, rebasing.structure_id)
    plan.nodes = {**plan.structure.tasks, **{each: new_id() for each in plan.added}}
    final = _places(plan, tree)
    created: dict[UUID, Node] = {}
    for lineage in plan.order:
        if lineage in plan.added:
            node = _new_node(rebasing, plan.nodes[lineage], lineage, TASK)
            node.origin_risk_id = plan.main.tree.nodes[plan.main.tasks[lineage]].origin_risk_id
            node.parent_id = final[node.id][0]
            created[node.id] = node
    _move(rebasing, tree, final, created, [plan.nodes[each] for each in plan.removed])
    session.add_all(_new_task(rebasing, plan, each) for each in plan.added)
    session.flush()
    _carried(rebasing, plan, tree)
    _linked(rebasing, plan, tree)


def _lists(plan: RebasePlan, tree: Tree, lines: LinesPlaced) -> dict[UUID, list[UUID]]:
    """Give the lines each task the update leaves bears, by lineage, in their order.

    The lines of the differential that stay under their task first, as it has them; then those that
    come from a task that leaves, in the order of the differential; then those the main structure
    places — added, or moved —, each after the sibling that precedes it in the main structure and
    that is there, first if none, last when it is not under the task it has there.
    """
    lists: dict[UUID, list[UUID]] = {each: [] for each in plan.order}
    nodes = tree.nodes
    ordered = [nodes[each] for each in tree.order if nodes[each].kind == LINE]
    task_of = {
        each.lineage_id: nodes[each.parent_id].lineage_id
        for each in ordered
        if each.parent_id is not None
    }
    for staying in (True, False):
        for node in ordered:
            lineage, task = node.lineage_id, lines.placed.get(node.lineage_id)
            if task is None or lineage in lines.by_main or (task_of[lineage] == task) != staying:
                continue
            lists[task].append(lineage)
    main = plan.main.tree
    in_main = {main.nodes[each].lineage_id: each for each in main.nodes if each not in main.tasks}
    order = {main.nodes[each].lineage_id: rank for rank, each in enumerate(main.order)}
    asked = dict(lines.created)
    asked.update({each: task for each in lines.by_main if (task := lines.placed[each]) is not None})
    for lineage in sorted(asked, key=order.__getitem__):
        task = asked[lineage]
        parent = main.nodes[in_main[lineage]].parent_id
        if parent is not None and main.nodes[parent].lineage_id == task:
            siblings = [main.nodes[each].lineage_id for each in main.lines(parent)]
            before = siblings[: siblings.index(lineage)]
            following = next((each for each in reversed(before) if each in lists[task]), None)
            at = 0 if following is None else lists[task].index(following) + 1
            lists[task].insert(at, lineage)
        else:
            lists[task].append(lineage)
    return lists


def write_lines(
    rebasing: StructureRebasing, plan: RebasePlan, lines: LinesPlaced
) -> dict[UUID, UUID]:
    """Write the nodes of the lines the update leaves; give the node of each line it creates.

    The lines that leave are deleted with their facet, then those the main structure adds are
    created under their task — their facet is the estimate's to write —, and each task's lines take
    their place; the lines whose place or facet changes are counted.
    """
    session, project_id = rebasing.session, rebasing.project_id
    tree = read_tree(session, project_id, rebasing.structure_id)
    own = {node.lineage_id: node.id for node in tree.nodes.values() if node.kind == LINE}
    gone = [own[each] for each, task in lines.placed.items() if task is None]
    if gone:
        deleted(session, project_id, tree, gone)
        tree = read_tree(session, project_id, rebasing.structure_id)
    lists = _lists(plan, tree, lines)
    main = plan.main.tree
    in_main = {main.nodes[each].lineage_id: each for each in main.nodes if each not in main.tasks}
    created: dict[UUID, Node] = {}
    for lineage in lines.created:
        node = _new_node(rebasing, new_id(), lineage, LINE)
        node.origin_risk_id = main.nodes[in_main[lineage]].origin_risk_id
        created[lineage] = node
    final: dict[UUID, tuple[UUID | None, int]] = {}
    for task, members in lists.items():
        parent = plan.nodes[task]
        held = [tree.nodes.get(own[each]) if each in own else None for each in members]
        for lineage, rank in zip(members, _numbered(parent, held), strict=True):
            final[own[lineage] if lineage in own else created[lineage].id] = (parent, rank)
    for node in created.values():
        node.parent_id = final[node.id][0]
    moved = _move(rebasing, tree, final, {node.id: node for node in created.values()}, [])
    for lineage in lines.changed:
        if own[lineage] not in moved:
            stamp(tree.nodes[own[lineage]], rebasing.act)
    session.flush()
    return {lineage: node.id for lineage, node in created.items()}


def finish(rebasing: StructureRebasing, plan: RebasePlan) -> None:
    """Delete the tasks that leave, replace the base, make the differential up to date, replay it.

    The base becomes a copy of the main structure as it is, which the differential is read against
    from now on; the differential bears the counter of the main structure, and is up to date. The
    engine is replayed once on the differential, which writes its dates and prices its lines again,
    all of them: a line may stand under another task, on other dates.
    """
    session, project_id = rebasing.session, rebasing.project_id
    tree = read_tree(session, project_id, rebasing.structure_id)
    # The links in conflict as the differential held them, read before the update wrote its links:
    # one the update deletes moves its ends that stay (``kept``).
    conflicts = conflicts_of(plan.structure.links.values())
    leaving = [plan.nodes[each] for each in plan.removed]
    if leaving:
        below = [line for each in leaving for line in tree.lines(each)]
        deleted(session, project_id, tree, [*leaving, *below])
    base = Place(project_id, rebasing.revision_id, rebasing.base_id)
    delete_structure_nodes(session, base)
    main, target = rebasing.main_structure_id, rebasing.base_id
    copy = RevisionCopy(
        session,
        project_id,
        rebasing.revision_id,
        rebasing.revision_id,
        rebasing.act.at,
        rebasing.act.author,
        {main: target},
        within_revision=True,
    )
    copy_structure_nodes(copy)
    rebased_structure(rebasing)
    repriced = tuple(plan.nodes[each] for each in plan.order)
    held = Holding(conflicts=conflicts, repriced=repriced)
    replayed(session, project_id, rebasing.structure_id, rebasing.act.at, held)
