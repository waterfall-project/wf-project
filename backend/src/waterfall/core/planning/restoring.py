# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The snapshots an undoing or a redoing gives back, restored under the rules of the entry.

The history hands the planning the objects to bring back as they were (``Restoring.restored``) and
those to delete (``Restoring.removed``); the planning rewrites them in the structure its frame
holds the lock of, then replays the engine on it (EP-06, "L'historique annulable et le collage").
It restores the rows of a snapshot as a write of the tree would write them — the counter of each
node advanced, its author and its instant those of the restoring — under the rules of the entry,
never over what another contributor did since:

- an object whose parent, place or element of the work breakdown another change has taken is a
  conflict (409 ``UNDO_CONFLICT``), the object that holds it named; a node deleted by the entry
  that created it must bear no node added since;
- an attachment to an element of the work breakdown that no longer exists, or is marked deleted,
  is not restored: the task comes back without it (#2501). A refusal would have to be declared by
  the contract, and an undoing of an unrelated cell must not fail for an element it never touched;
- the links and the inscriptions follow their entry: a node created again takes back all of its
  own, a node changed only those its entry writes — the predecessors of a task for a ``link``, its
  inscriptions for a ``tracking`` —, and a link or an inscription whose other end, or timeline, is
  gone is left out.
"""

import annotationlib
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast, get_args
from uuid import UUID

from sqlalchemy import select

from waterfall.core.history.interface import UNDO_CONFLICT, ObjectState
from waterfall.core.planning.attachments import ORDER_ITEM_ID, WORK_PACKAGE_ID, carriers
from waterfall.core.planning.dating import conflicts_of
from waterfall.core.planning.interface.snapshots import snapshot
from waterfall.core.planning.interface.structures import structure_state
from waterfall.core.planning.shaping import PARKED, deleted
from waterfall.core.planning.tables import Node, Task, TaskLink, Timeline, TrackingEntry
from waterfall.core.planning.tree import read_links, read_tree, tracking_of
from waterfall.core.planning.writing import redated_structure
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.core.revisions.interface import structure_facts, write_structure
from waterfall.platform.errors import ConflictError, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, Restoring, Snapshot
    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import NodesWritten, Place, Writer
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.database import Base

# The columns a restoring leaves to the node that bears them, and to its facet.
NODE_KEPT = frozenset({"project_id", "id", "revision_id", "structure_id", "lineage_id", "kind"})
NODE_STAMPED = frozenset({"lock_version", "created_at", "created_by", "updated_at", "updated_by"})
TASK_KEPT = frozenset({"project_id", "node_id", "structure_id", "kind"})
# The entries that write the links of a task, and its inscriptions.
LINK = "link"
TRACKING = "tracking"


def structure_of(states: Snapshot) -> UUID:
    """Give the structure the objects of an entry belong to, by what their rows say.

    A node names its structure; the structure itself is the object of a ``structure_update``.
    """
    for state in states:
        node = state.rows.get("node")
        if isinstance(node, dict):
            return UUID(cast("str", node["structure_id"]))
        if "structure" in state.rows:
            return state.object_id
    msg = "an entry of the history names a structure, by a node or by itself"
    raise RuntimeError(msg)


def read_objects(session: Session, project_id: UUID, object_ids: tuple[UUID, ...]) -> Snapshot:
    """Give the objects named as they are: the nodes, and the structures of a ``structure_update``.

    Those absent are left out.
    """
    found = snapshot(session, project_id, object_ids)
    known = {state.object_id for state in found}
    structures: list[ObjectState] = []
    for each in object_ids:
        if each in known:
            continue
        try:
            facts = structure_facts(session, project_id, each, lock=False)
        except NotFoundError:
            continue
        structures.append(structure_state(facts))
    return (*found, *structures)


def _conflict(object_id: UUID, label: str) -> ConflictError:
    """Refuse an entry that cannot be brought back over what has been written since."""
    return ConflictError(
        UNDO_CONFLICT,
        {"conflicting_object_id": str(object_id), "conflicting_object_label": label},
    )


def _label(tree: Tree, node_id: UUID) -> str:
    """Give the label of a task of the tree, none for another node."""
    task = tree.tasks.get(node_id)
    return "" if task is None else task.label


def _coerced(kind: type, value: JsonValue) -> object:
    """Give a column kept as JSON in the type of its table: identifiers, decimals, dates."""
    if value is None or not isinstance(value, str):
        return value
    if kind is UUID:
        return UUID(value)
    if kind is Decimal:
        return Decimal(value)
    if kind is datetime:
        return datetime.fromisoformat(value)
    if kind is date:
        return date.fromisoformat(value)
    return value


def _kinds(table: type[Base]) -> dict[str, type]:
    """Give the Python type each column of a table is declared with, by name.

    Read from the annotations of its class and of the classes it extends (``Mapped[UUID | None]``
    is a ``UUID``): the type of a column that names another table's, or that a decorator wraps, is
    not known to the column before the tables are bound.
    """
    found: dict[str, type] = {}
    for each in reversed(table.__mro__):
        annotations = annotationlib.get_annotations(each, format=annotationlib.Format.FORWARDREF)
        for name, hint in annotations.items():
            declared = get_args(hint)
            if declared:
                members = [kind for kind in get_args(declared[0]) if kind is not type(None)]
                found[name] = members[0] if members else declared[0]
    return found


def _typed(table: type[Base], row: Mapping[str, JsonValue]) -> dict[str, object]:
    """Give the columns of a row kept as JSON, in the types of the table that holds it."""
    kinds = _kinds(table)
    return {name: _coerced(kinds[name], value) for name, value in row.items() if name in kinds}


def _row(state: ObjectState, name: str) -> Mapping[str, JsonValue]:
    """Give the rows of a snapshot kept under a name: the node, the task."""
    return cast("Mapping[str, JsonValue]", state.rows[name])


def _list(state: ObjectState, name: str) -> list[Mapping[str, JsonValue]]:
    """Give the rows of a snapshot kept as a list: the links, the inscriptions."""
    return cast("list[Mapping[str, JsonValue]]", state.rows[name])


def _id(row: Mapping[str, JsonValue], name: str) -> UUID | None:
    """Give an identifier of a row kept as JSON, none if null."""
    value = row[name]
    return None if value is None else UUID(cast("str", value))


@dataclass(frozen=True, slots=True)
class Restoration:
    """A restoring judged: the objects to bring back, split by whether the tree holds them.

    ``bearing`` is the attachment each task brings back keeps: the element of the work breakdown
    it names, or none if that element is gone since.
    """

    created: tuple[ObjectState, ...]
    changed: tuple[ObjectState, ...]
    removed: tuple[UUID, ...]
    bearing: Mapping[UUID, tuple[UUID | None, UUID | None]]


def _judged(session: Session, project_id: UUID, tree: Tree, restoring: Restoring) -> Restoration:
    """Judge the restoring on the tree as it is under the lock: refuse it or split its objects.

    A conflict names the object another change holds; the attachments to a work breakdown element
    gone are dropped from what is restored.
    """
    removed = tuple(each for each in restoring.removed if each in tree.nodes)
    states = restoring.restored
    kept = {state.object_id for state in states}
    created = tuple(state for state in states if state.object_id not in tree.nodes)
    changed = tuple(state for state in states if state.object_id in tree.nodes)
    for node_id in removed:
        for child in tree.children.get(node_id, []):
            if child not in removed:
                raise _conflict(child, _label(tree, child))
    outside = set(tree.nodes) - kept - set(removed)
    holders = {
        (tree.nodes[each].parent_id, tree.nodes[each].kind, tree.nodes[each].rank): each
        for each in outside
    }
    present = (set(tree.nodes) - set(removed)) | {state.object_id for state in created}
    for state in states:
        node = _row(state, "node")
        parent = _id(node, "parent_id")
        if parent is not None and parent not in present:
            raise _conflict(state.object_id, state.label)
        place = (parent, cast("str", node["kind"]), cast("int", node["rank"]))
        if place in holders:
            raise _conflict(holders[place], _label(tree, holders[place]))
    return Restoration(created, changed, removed, _bearing(session, project_id, tree, restoring))


def _bearing(
    session: Session, project_id: UUID, tree: Tree, restoring: Restoring
) -> dict[UUID, tuple[UUID | None, UUID | None]]:
    """Give the attachment each task brought back keeps, an element gone since dropped (#2501).

    An element another task of the structure bears now is a conflict, that task named: the element
    is borne by one task of a structure at most.
    """
    asked = {
        state.object_id: (
            _id(_row(state, "task"), WORK_PACKAGE_ID),
            _id(_row(state, "task"), ORDER_ITEM_ID),
        )
        for state in restoring.restored
        if state.rows["task"] is not None
    }
    wanted = [item for pair in asked.values() for item in pair if item is not None]
    items = work_breakdown_items(session, project_id, shared=wanted) if wanted else {}
    borne = carriers(tree)
    brought = {state.object_id for state in restoring.restored} | set(restoring.removed)
    kept: dict[UUID, tuple[UUID | None, UUID | None]] = {}
    for node_id, pair in asked.items():
        live: list[UUID | None] = []
        for item_id in pair:
            item = None if item_id is None else items.get(item_id)
            if item_id is None or item is None or item.deleted:
                live.append(None)
                continue
            holder = borne.get(item_id)
            if holder is not None and holder != node_id and holder not in brought:
                raise _conflict(holder, _label(tree, holder))
            live.append(item_id)
        kept[node_id] = (live[0], live[1])
    return kept


def _park(tree: Tree, changed: tuple[ObjectState, ...]) -> None:
    """Park the rank of every node brought back, so that the places exchange at their turn."""
    for turn, state in enumerate(changed, start=1):
        tree.nodes[state.object_id].rank = PARKED + turn


def _write_changed(tree: Tree, restoration: Restoration, writer: Writer) -> None:
    """Rewrite the rows of the nodes the tree holds, their counter advanced."""
    act = writer.act
    for state in restoration.changed:
        node, task = tree.nodes[state.object_id], tree.tasks[state.object_id]
        for column, value in _typed(Node, _row(state, "node")).items():
            if column not in NODE_KEPT | NODE_STAMPED:
                setattr(node, column, value)
        node.lock_version += 1
        node.updated_at, node.updated_by = act.at, act.author
        for column, value in _typed(Task, _row(state, "task")).items():
            if column not in TASK_KEPT:
                setattr(task, column, value)
        task.work_package_id, task.order_item_id = restoration.bearing[state.object_id]


def _depth(states: tuple[ObjectState, ...]) -> list[ObjectState]:
    """Order the nodes to create so that each parent comes before its children."""
    parents = {state.object_id: _id(_row(state, "node"), "parent_id") for state in states}
    by_id = {state.object_id: state for state in states}

    def depth(node_id: UUID) -> int:
        above = parents[node_id]
        return 0 if above is None or above not in by_id else 1 + depth(above)

    return sorted(states, key=lambda state: depth(state.object_id))


def _write_created(session: Session, restoration: Restoration, writer: Writer) -> None:
    """Insert the nodes brought back again, with their facet, at the counter that follows."""
    act = writer.act
    ordered = _depth(restoration.created)
    for state in ordered:
        columns = _typed(Node, _row(state, "node"))
        columns["lock_version"] = state.lock_version + 1
        columns["updated_at"], columns["updated_by"] = act.at, act.author
        session.add(Node(**columns))
    session.flush()
    for state in ordered:
        columns = _typed(Task, _row(state, "task"))
        columns["work_package_id"], columns["order_item_id"] = restoration.bearing[state.object_id]
        session.add(Task(**columns))
    session.flush()


def _restore_links(session: Session, place: Place, restoration: Restoration, kind: str) -> None:
    """Give the links back: all those of a node created again, a task's predecessors for a link.

    The other end must stand in the structure, and a link of the same two tasks already there is
    kept, its type and its lag brought back for a task whose predecessors the entry wrote.
    """
    wanted: dict[tuple[UUID, UUID], Mapping[str, JsonValue]] = {}
    for state in restoration.created:
        for row in _list(state, "links"):
            wanted[_ends(row)] = row
    entered: set[UUID] = (
        {state.object_id for state in restoration.changed} if kind == LINK else set()
    )
    ends = {
        (link.predecessor_id, link.successor_id): link
        for link in read_links(session, place.project_id, place.structure_id)
    }
    for state in restoration.changed:
        if state.object_id not in entered:
            continue
        own = {_ends(row): row for row in _list(state, "links") if _ends(row)[1] == state.object_id}
        wanted.update(own)
        for pair in [pair for pair in ends if pair[1] == state.object_id and pair not in own]:
            session.delete(ends.pop(pair))
    nodes = set(
        session.scalars(
            select(Node.id).where(
                Node.project_id == place.project_id, Node.structure_id == place.structure_id
            )
        )
    )
    for pair, row in wanted.items():
        current = ends.get(pair)
        if current is not None:
            for name, value in _typed(TaskLink, row).items():
                if pair[1] in entered and name in {"link_type", "lag_value", "lag_unit"}:
                    setattr(current, name, value)
        elif pair[0] in nodes and pair[1] in nodes:
            session.add(TaskLink(**_typed(TaskLink, row)))
    session.flush()


def _ends(row: Mapping[str, JsonValue]) -> tuple[UUID, UUID]:
    """Give the two tasks a link of a snapshot binds, predecessor first."""
    return cast("UUID", _id(row, "predecessor_id")), cast("UUID", _id(row, "successor_id"))


def _restore_tracking(
    session: Session, project_id: UUID, restoration: Restoration, kind: str
) -> None:
    """Give the inscriptions back: all those of a node created again, a task's for a tracking.

    The lineage of a task bears them; one whose timeline is deleted since is left out, and one the
    lineage holds again is kept.
    """
    entered = restoration.changed if kind == TRACKING else ()
    states = (*restoration.created, *entered)
    if not states:
        return
    timelines = set(session.scalars(select(Timeline.id).where(Timeline.project_id == project_id)))
    lineages = {state.object_id: _id(_row(state, "node"), "lineage_id") for state in states}
    held = tracking_of(session, project_id, {each for each in lineages.values() if each})
    for state in states:
        lineage = lineages[state.object_id]
        if lineage is None:
            continue
        current = {(entry.kind, entry.timeline_id): entry for entry in held[lineage]}
        wanted = {
            (cast("str", row["kind"]), _id(row, "timeline_id")): row
            for row in _list(state, "tracking")
            if _id(row, "timeline_id") in {None, *timelines}
        }
        if state in entered:
            for key in [key for key in current if key not in wanted]:
                session.delete(current[key])
        for key, row in wanted.items():
            if key not in current:
                session.add(TrackingEntry(**_typed(TrackingEntry, row)))
    session.flush()


def _restore_structure(
    session: Session, place: Place, facts: StructureFacts, restoring: Restoring, writer: Writer
) -> NodesWritten:
    """Bring back the start date and the label of a structure, and redate it."""
    [state] = restoring.restored
    rows = cast("Mapping[str, str]", state.rows["structure"])
    start = date.fromisoformat(rows["planning_start_on"])
    conflicts = conflicts_of(read_links(session, place.project_id, place.structure_id))
    write_structure(
        session, place.project_id, place.structure_id, (start, rows["label"]), writer.act
    )
    facts = replace(facts, planning_start_on=start, label=rows["label"])
    redated = redated_structure(session, place, writer.act, (facts, None, conflicts))
    restoring.keep_present((structure_state(replace(facts, lock_version=redated.counter)),))
    return redated.written(())


def restore(
    session: Session,
    place: Place,
    facts: StructureFacts,
    restoring: Restoring,
    writer: Writer,
) -> NodesWritten:
    """Restore the objects an entry gives back, under the lock of its structure, and redate it.

    ``facts`` are those of the structure read under the lock the frame of the history took, not
    read again. The nodes of the entry that its undoing deletes go first, those it brings back are
    rewritten, or written again with their facet, their links and inscriptions; the engine is then
    replayed on the structure. The objects as they are left are handed to the frame
    (``Restoring.keep_present``). Refused by 409 ``UNDO_CONFLICT`` when another change holds what
    the entry would take back (see the module); nothing is written then.
    """
    if any("structure" in state.rows for state in restoring.restored):
        return _restore_structure(session, place, facts, restoring, writer)
    project_id, structure_id = place.project_id, place.structure_id
    tree = read_tree(session, project_id, structure_id)
    conflicts = conflicts_of(read_links(session, project_id, structure_id))
    restoration = _judged(session, project_id, tree, restoring)
    removed = restoration.removed
    former = tuple(
        dict.fromkeys(
            above for each in removed for above in tree.ancestors(each) if above not in removed
        )
    )
    if removed:
        deleted(session, project_id, tree, list(removed))
    _park(tree, restoration.changed)
    session.flush()
    _write_changed(tree, restoration, writer)
    session.flush()
    _write_created(session, restoration, writer)
    _restore_links(session, place, restoration, restoring.kind)
    _restore_tracking(session, project_id, restoration, restoring.kind)
    redated = redated_structure(session, place, writer.act, (facts, None, conflicts))
    ids = tuple(state.object_id for state in restoring.restored)
    restoring.keep_present(snapshot(session, project_id, ids))
    return redated.written(ids, former)
