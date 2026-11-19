# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the planning in the merge of a differential (WF-REV-0050; EP-08, "Modules").

``merge_tasks`` is its part of ``register_merge``: the tasks and the links of the differential
matched with the main structure by their lineage — added, updated, removed, or kept and completed
when started (``merging``) —; ``merge_end`` its part of ``register_merge_end``: what refuses the
merge, judged once on the structure the merge leaves (WF-PLA-0030, WF-PLA-0150, WF-PLA-0170). The
estimate, whose part comes after, reads of the same plan where each line stands
(``merged_lines``): in the main structure and in the differential, by the lineage of its task, the
provisions told; which tasks the merge keeps, and where the provision lines of a task it removes
go — to the nearest ancestor it leaves, or, from the first level, to the first task of the first
level (WF-RIS-0010; #789).

The report reads; the application (US-2560/L2) writes what the same plan finds, under the lock of
the two structures.

Written by US-2560/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.merging import merge_plan, merge_refusals, task_differences
from waterfall.core.planning.tree import LINE
from waterfall.core.revisions.interface import MergePart

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from waterfall.core.planning.tree import NodeRow, TaskRow, Tree
    from waterfall.core.revisions.interface import StructureMerging


@dataclass(frozen=True, slots=True)
class MergedLine:
    """A line of a structure merged: its node, its lineage, its task's, if it is a provision."""

    node_id: UUID
    lineage_id: UUID
    task_lineage_id: UUID
    is_provision: bool


@dataclass(frozen=True, slots=True)
class MergedLines:
    """Where the lines of a merge stand, each structure in the order of its plan.

    ``kept`` the lineages of the tasks the differential removes and the merge keeps, started;
    ``moved`` the lineage of each task it removes whose provision lines go to another task, with
    the node of that task — in the main structure, or in the differential for a task it adds.
    """

    main: tuple[MergedLine, ...]
    amendment: tuple[MergedLine, ...]
    kept: frozenset[UUID]
    moved: Mapping[UUID, UUID]


def merge_tasks(merging: StructureMerging) -> MergePart:
    """Give the part of the planning in a merge: its tasks and its links, the tasks it completes."""
    differences, completed = task_differences(merging)
    return MergePart(differences=differences, completed_tasks=completed)


def merge_end(merging: StructureMerging) -> MergePart:
    """Judge the structure a merge leaves, once every part is given (#3946); give its refusals."""
    return MergePart(refusals=merge_refusals(merging))


def lines_in_order(tree: Tree[NodeRow, TaskRow]) -> tuple[MergedLine, ...]:
    """Give the lines of a structure in the order of its plan, by the lineage of their task."""
    found: list[MergedLine] = []
    for node_id in tree.order:
        node = tree.nodes[node_id]
        if node.kind != LINE or node.parent_id is None:
            continue
        task = tree.nodes[node.parent_id].lineage_id
        found.append(MergedLine(node_id, node.lineage_id, task, node_id in tree.provisions))
    return tuple(found)


def merged_lines(merging: StructureMerging) -> MergedLines:
    """Tell the estimate where the lines of a merge stand, of the plan the planning built."""
    plan = merge_plan(merging)
    first = plan.order[0] if plan.order else None
    moved: dict[UUID, UUID] = {}
    for task_id in plan.removed:
        target = plan.staying(task_id) or first
        if target is not None:
            moved[plan.main.nodes[task_id].lineage_id] = target
    kept = frozenset(plan.main.nodes[each].lineage_id for each in plan.kept)
    return MergedLines(lines_in_order(plan.main), lines_in_order(plan.amendment), kept, moved)
