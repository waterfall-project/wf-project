# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predecessors of a task: its links replaced, the engine replayed (``setPredecessors``).

The links of a task to its predecessors are replaced at once, each kept with its type, its lag and
the unit of its lag, a negative lag a lead (WF-PLA-0030, WF-PLA-0160). They are judged under the
lock of the structure, after its counter (412): a predecessor named twice
(``DUPLICATE_PREDECESSOR``) or that is no task of the structure (``UNKNOWN_TASK``), each at its
rank; then by the engine, on the structure the links would leave — a loop of links, the shortest
named from the task entered (``LINK_CYCLE``, a task its own predecessor a loop of itself), a link
between a summary and its subordinate (``LINK_FORBIDDEN``), a project carried beyond fifteen years,
the task entered named (``PROJECT_HORIZON_EXCEEDED``) (EP-06, US-1390). Nothing is written then.

Declared by US-1380/L1; filled by US-1390/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import insert, select

from waterfall.core.planning.dating import LINK_CYCLE
from waterfall.core.planning.scheduling import Entry
from waterfall.core.planning.tables import TaskLink
from waterfall.core.planning.writing import writing
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import NodesWritten, Place, Writer

DUPLICATE_PREDECESSOR = "DUPLICATE_PREDECESSOR"
UNKNOWN_TASK = "UNKNOWN_TASK"


@dataclass(frozen=True, slots=True)
class PredecessorSent:
    """A predecessor as it is sent: its task, the type of the link, its lag in its unit."""

    predecessor_id: UUID
    link_type: str
    lag_value: Decimal
    lag_unit: str


@dataclass(frozen=True, slots=True)
class PredecessorsEntry:
    """The predecessors that replace a task's, in the order sent, at the counter read."""

    predecessors: tuple[PredecessorSent, ...]
    lock_version: int


def _faults(tree: Tree, sent: tuple[PredecessorSent, ...]) -> list[FieldError]:
    """Name each predecessor sent again after its first, or that is no task of the structure."""
    faults: list[FieldError] = []
    seen: set[UUID] = set()
    for rank, each in enumerate(sent):
        pointer = f"/predecessors/{rank}/predecessor_node_id"
        if each.predecessor_id in seen:
            faults.append(FieldError(pointer, DUPLICATE_PREDECESSOR))
        elif each.predecessor_id not in tree.tasks:
            faults.append(FieldError(pointer, UNKNOWN_TASK))
        seen.add(each.predecessor_id)
    return faults


def set_predecessors(
    session: Session, place: Place, node_id: UUID, entry: PredecessorsEntry, writer: Writer
) -> NodesWritten:
    """Replace the predecessors of a task at the counter read, and give the nodes written.

    Refused if the node is no task of the structure (404), at another version (412), or for links
    the rules refuse (422); the task's version advances, its successors and what the critical path
    shifts are given redated (``rescheduled``), the summaries above (``ancestors``).
    """
    with writing(session, place, writer, ("link", (node_id,))) as write:
        tree = write.tree
        if node_id not in tree.tasks:
            raise NotFoundError(NOT_FOUND)
        node, task = tree.nodes[node_id], tree.tasks[node_id]
        if node.lock_version != entry.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        faults = _faults(tree, entry.predecessors)
        if faults:
            raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
        if any(each.predecessor_id == node_id for each in entry.predecessors):
            # The base holds no link of a task to itself: the loop is named before any write.
            named = [{"node_id": str(node_id), "label": task.label}]
            raise UnprocessableError(LINK_CYCLE, {"cycle": named})
        write.before((node_id,))
        _replace(session, place, node_id, entry.predecessors)
        node.lock_version += 1
        node.updated_at = writer.act.at
        node.updated_by = writer.act.author
        # A predecessor whose link in conflict is withdrawn loses its signal: it moved too, which
        # the replay judges against the links in conflict read before the write.
        redated = write.redate((node_id, task.label), Entry(node_id))
        write.after((node_id,))
        return redated.written((node_id,))


def _replace(
    session: Session, place: Place, node_id: UUID, sent: tuple[PredecessorSent, ...]
) -> None:
    """Write the links sent to a task, those it keeps changed in place, the others deleted.

    A link kept keeps its row and its signal of conflict until the engine judges it again.
    """
    held = {
        link.predecessor_id: link
        for link in session.scalars(
            select(TaskLink).where(
                TaskLink.project_id == place.project_id,
                TaskLink.structure_id == place.structure_id,
                TaskLink.successor_id == node_id,
            )
        )
    }
    wanted = {each.predecessor_id for each in sent}
    for predecessor, link in held.items():
        if predecessor not in wanted:
            session.delete(link)
    added: list[dict[str, object]] = []
    for each in sent:
        link = held.get(each.predecessor_id)
        if link is None:
            added.append(
                {
                    "project_id": place.project_id,
                    "id": new_id(),
                    "revision_id": place.revision_id,
                    "structure_id": place.structure_id,
                    "predecessor_id": each.predecessor_id,
                    "successor_id": node_id,
                    "link_type": each.link_type,
                    "lag_value": each.lag_value,
                    "lag_unit": each.lag_unit,
                    "in_conflict": False,
                }
            )
            continue
        link.link_type = each.link_type
        link.lag_value = each.lag_value
        link.lag_unit = each.lag_unit
    session.flush()
    if added:
        session.execute(insert(TaskLink), added)
