# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of the nodes of a revision opened from a marked one: nodes, tasks and links.

Registered after the copy of the structures (``register_copy``), whose copies it finds in
``RevisionCopy.identifiers``. Each table is copied by one ``INSERT … SELECT``, joined to the
identifiers and those of their copies (``copies``): the rows never leave the database. Sent one by
one, a thousand tasks and five thousand lines cost the opening of a revision most of its ten
seconds (US-2240, #3102). Moved out of ``nodes`` by US-2240/L2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Integer, Uuid, case, insert, literal, null, select

from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.database import Base, UtcDateTime, among, copied_columns, copies
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from typing import Any
    from uuid import UUID

    from sqlalchemy import ColumnElement

    from waterfall.core.revisions.interface import RevisionCopy

NODE = Base.metadata.tables[Node.__tablename__]
TASK = Base.metadata.tables[Task.__tablename__]
LINK = Base.metadata.tables[TaskLink.__tablename__]


def _stamp(copy: RevisionCopy) -> dict[str, ColumnElement[Any]]:
    """Give the stamp of the copies: the creation of the revision, its instant and its author."""
    at, author = literal(copy.at, UtcDateTime()), literal(copy.author, Uuid())
    return {"created_at": at, "created_by": author, "updated_at": at, "updated_by": author}


def _copy_tasks(
    copy: RevisionCopy,
    nodes: dict[UUID, UUID],
    structures: dict[UUID, UUID],
    *,
    attached: bool,
) -> None:
    """Copy the facet task of the nodes copied, its attachment to an element deleted left null.

    A task copied unattached bears none: the work breakdown is the main structure's alone.
    """
    session = copy.session
    gone = [
        item.item_id
        for item in work_breakdown_items(session, copy.project_id).values()
        if item.deleted
    ]
    node, structure = copies(nodes, "copied_node"), copies(structures, "copied_structure")
    kept = (
        {
            "work_package_id": case(
                (among(TASK.c.work_package_id, gone), None), else_=TASK.c.work_package_id
            ),
            "order_item_id": case(
                (among(TASK.c.order_item_id, gone), None), else_=TASK.c.order_item_id
            ),
        }
        if attached
        else {"work_package_id": null(), "order_item_id": null()}
    )
    names, columns = copied_columns(
        TASK, {"node_id": node.c.copy, "structure_id": structure.c.copy, **kept}
    )
    rows = (
        select(*columns)
        .select_from(TASK)
        .join(node, node.c.source == TASK.c.node_id)
        .join(structure, structure.c.source == TASK.c.structure_id)
        .where(TASK.c.project_id == copy.project_id)
    )
    session.execute(insert(TASK).from_select(names, rows))


def _copy_links(copy: RevisionCopy, nodes: dict[UUID, UUID], structures: dict[UUID, UUID]) -> None:
    """Copy the links of the structures copied, each under an identifier of its own."""
    session = copy.session
    links = {
        each: new_id()
        for each in session.scalars(
            select(TaskLink.id).where(
                TaskLink.project_id == copy.project_id,
                TaskLink.revision_id == copy.source,
                among(TaskLink.structure_id, structures),
            )
        )
    }
    if not links:
        return
    # The joins on the nodes lose no link: a link keeps its two tasks in its own structure
    # (``_in_structure``), and every node of a structure copied is copied above.
    link, structure = copies(links, "copied_link"), copies(structures, "copied_structure")
    predecessor, successor = copies(nodes, "predecessor"), copies(nodes, "successor")
    names, columns = copied_columns(
        LINK,
        {
            "id": link.c.copy,
            "revision_id": literal(copy.target, Uuid()),
            "structure_id": structure.c.copy,
            "predecessor_id": predecessor.c.copy,
            "successor_id": successor.c.copy,
        },
    )
    rows = (
        select(*columns)
        .select_from(LINK)
        .join(link, link.c.source == LINK.c.id)
        .join(structure, structure.c.source == LINK.c.structure_id)
        .join(predecessor, predecessor.c.source == LINK.c.predecessor_id)
        .join(successor, successor.c.source == LINK.c.successor_id)
        .where(LINK.c.project_id == copy.project_id)
    )
    session.execute(insert(LINK).from_select(names, rows))


def _copy(copy: RevisionCopy, *, attached: bool) -> None:
    """Copy the nodes of the source, their facet task and their links (WF-DAT-0010).

    The nodes of each structure copied, under identifiers of their own and their lineage, at their
    place, at their first version, their dates as computed, their attachment to the work breakdown
    but to an element marked deleted, which the revision opened does not take up (WF-PLA-0170); the
    facets the later modules register after them (``register_facet``). The inscriptions follow the
    lineage, and stay.
    """
    session, ids = copy.session, copy.identifiers
    sources = session.execute(
        select(Node.id, Node.structure_id).where(
            Node.project_id == copy.project_id, Node.revision_id == copy.source
        )
    ).all()
    nodes = {each: new_id() for each, structure_id in sources if structure_id in ids}
    if not nodes:
        return
    structures = {
        structure_id: ids[structure_id] for each, structure_id in sources if each in nodes
    }
    ids.update(nodes)
    node, structure = copies(nodes, "copied_node"), copies(structures, "copied_structure")
    parent = copies(nodes, "copied_parent")
    names, columns = copied_columns(
        NODE,
        {
            "id": node.c.copy,
            "revision_id": literal(copy.target, Uuid()),
            "structure_id": structure.c.copy,
            "parent_id": parent.c.copy,
            "lock_version": literal(1, Integer()),
            **_stamp(copy),
        },
    )
    # One statement: the reference of a node to its parent is checked once it ends, whatever the
    # order the rows are written in.
    rows = (
        select(*columns)
        .select_from(NODE)
        .join(node, node.c.source == NODE.c.id)
        .join(structure, structure.c.source == NODE.c.structure_id)
        .outerjoin(parent, parent.c.source == NODE.c.parent_id)
        .where(NODE.c.project_id == copy.project_id)
    )
    session.execute(insert(NODE).from_select(names, rows))
    _copy_tasks(copy, nodes, structures, attached=attached)
    _copy_links(copy, nodes, structures)
    for hooks in facets().values():
        hooks.copy(copy)


def copy_nodes(copy: RevisionCopy) -> None:
    """Copy the nodes of a revision opened from a marked one, attachments kept (WF-DAT-0010)."""
    _copy(copy, attached=True)


def copy_structure_nodes(copy: RevisionCopy) -> None:
    """Copy the nodes of a structure into another of the same revision, a differential's.

    As the copy of a revision does, the source being the revision itself (``source`` and ``target``
    are one): the nodes keep their lineage, and the facets their figures as they are — a line its
    budgeted amount, not the reference's again. The tasks copied bear no attachment to the work
    breakdown, which the main structure alone carries (WF-PLA-0170).
    """
    _copy(copy, attached=False)
