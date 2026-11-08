# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The snapshots of the nodes the history keeps, and their restitution.

Each write of the planning takes the snapshot of the nodes it creates, changes or deletes — their
rows of ``node``, ``task``, ``task_link`` and ``tracking_entry`` — before and after it, and hands
both to the history (``history.recording``), which keeps them without reading any table of the
planning (EP-06, "L'historique annulable"). An undoing or a redoing gives back a snapshot, which
the planning restores — rows created, changed or deleted — under the rules of the entry, then
redates the structure.

Declared by US-1380/L1; ``snapshot`` filled by US-1380/L2: each node present, in the order named,
at its version, named by the label of its task, its rows written as JSON holds them — under
``node`` and ``task`` its rows, under ``links`` those of the links it is an end of, under
``tracking`` the inscriptions of its lineage. A node absent is left out: one a write creates is
absent before it, one it deletes after it. ``restore`` is US-1450/L2's, which gives its arguments
and its result.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import inspect, select

from waterfall.core.history.interface import ObjectState
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import links_of, tracking_of

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, Snapshot
    from waterfall.platform.database import Base


def _value(value: object) -> JsonValue:
    """Give a value of a column as JSON holds it: identifiers, decimals and dates as text."""
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if value is None or isinstance(value, bool | int | str):
        return value
    msg = f"a column of the planning holds no {type(value).__name__}"
    raise TypeError(msg)


def _row(row: Base) -> dict[str, JsonValue]:
    """Give the columns of a row, by name, as JSON holds them."""
    return {
        column.key: _value(getattr(row, column.key)) for column in inspect(row).mapper.column_attrs
    }


def snapshot(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> Snapshot:
    """Give the rows of the nodes named, their facets, links and inscriptions, as they are."""
    if not node_ids:
        return ()
    session.flush()
    nodes = {
        node.id: node
        for node in session.scalars(
            select(Node)
            .where(Node.project_id == project_id, Node.id.in_(node_ids))
            .execution_options(populate_existing=True)
        )
    }
    tasks = {
        task.node_id: task
        for task in session.scalars(
            select(Task)
            .where(Task.project_id == project_id, Task.node_id.in_(node_ids))
            .execution_options(populate_existing=True)
        )
    }
    links = links_of(session, project_id, nodes)
    tracking = tracking_of(session, project_id, {node.lineage_id for node in nodes.values()})
    states: list[ObjectState] = []
    for node_id in dict.fromkeys(node_ids):
        node = nodes.get(node_id)
        if node is None:
            continue
        task = tasks.get(node_id)
        rows: dict[str, JsonValue] = {
            "node": _row(node),
            "task": None if task is None else _row(task),
            "links": [_row(link) for link in links[node_id]],
            "tracking": [_row(entry) for entry in tracking[node.lineage_id]],
        }
        label = "" if task is None else task.label
        states.append(ObjectState(node_id, node.lock_version, label, rows))
    return tuple(states)


def restore(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Restore the rows of a snapshot the history gives back, and redate the structure."""
    msg = "restore is filled by US-1450/L2"
    raise NotImplementedError(msg)
