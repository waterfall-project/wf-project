# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The facet estimate line of a node: what the planning asks of it, by the hooks of its kind.

The planning knows no facet but the task's: it asks the hooks the estimate registers for the kind
``estimate_line`` (``register_facet``, EP-06, "Les points d'extension") — read the facets of the
nodes named, copy them into a revision opened, delete them with their nodes, give the calendars of
the roles of the lines of a task —, and those EP-07 adds to ``FacetHooks``: create the facet of a
node created, its snapshot and its restoration for the history, the judgment of a cell pasted, the
amounts of the lines of the nodes redated or moved, and the filters, the sort and the totals of the
lines for ``listNodes`` (EP-07, "Les points d'extension").

Declared by US-1490/L1, unregistered: US-1490/L3 registers the facet (``LINE_FACET``) once it
reads and creates a line, completes ``FacetHooks`` in the planning, and gives each hook its
arguments and its result; each raises ``NotImplementedError`` naming the story that fills it.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.planning.interface import FacetHooks

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionCopy


def read_lines(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> Mapping[UUID, Any]:
    """Give the facet of each line named, by node, as ``listNodes`` returns it."""
    msg = "read_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def copy_lines(copy: RevisionCopy) -> None:
    """Copy the lines of the nodes copied into the revision opened, their budgeted amounts kept."""
    msg = "copy_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def delete_lines(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> None:
    """Delete the lines of the nodes deleted."""
    msg = "delete_lines is filled by US-1490/L4"
    raise NotImplementedError(msg)


def line_calendars(session: Session, project_id: UUID, task_id: UUID) -> Collection[UUID]:
    """Give the calendars of the roles of the labour lines of a task (WF-PLA-0010)."""
    msg = "line_calendars is filled by US-1490/L3"
    raise NotImplementedError(msg)


def create_line(session: Session, project_id: UUID, node_id: UUID) -> None:
    """Create the facet of a line created, priced in the transaction (``createNode``)."""
    msg = "create_line is filled by US-1490/L3"
    raise NotImplementedError(msg)


def snapshot_lines(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> None:
    """Give the facets of the lines named as the history keeps them, to restore them."""
    msg = "snapshot_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def restore_lines(session: Session, project_id: UUID) -> None:
    """Write back the facets of lines a snapshot kept, as an undo or a redo asks."""
    msg = "restore_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def judge_line_cell(session: Session, project_id: UUID, node_id: UUID) -> None:
    """Judge a cell pasted on a line, in the order of ``NodeColumn``."""
    msg = "judge_line_cell is filled by US-1560"
    raise NotImplementedError(msg)


def reinflate_lines(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> None:
    """Price again the lines of the nodes redated or moved, and give those whose amounts moved."""
    msg = "reinflate_lines is filled by US-1490/L3"
    raise NotImplementedError(msg)


def line_filters() -> None:
    """Give the filters of ``listNodes`` on the columns of a line."""
    msg = "line_filters is filled by US-1490/L3"
    raise NotImplementedError(msg)


def line_sort() -> None:
    """Give the sort of ``listNodes`` on the columns of a line."""
    msg = "line_sort is filled by US-1490/L3"
    raise NotImplementedError(msg)


def line_totals() -> None:
    """Give the totals of the lines ``listNodes`` returns."""
    msg = "line_totals is filled by US-1490/L3"
    raise NotImplementedError(msg)


# The hooks of the kind ``estimate_line``, which US-1490/L3 registers in the planning.
LINE_FACET = FacetHooks(
    read=read_lines, copy=copy_lines, delete=delete_lines, calendars=line_calendars
)
