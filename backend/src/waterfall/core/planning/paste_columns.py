# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The columns a block pasted fills, by kind of node: the task's, the line's (WF-IHM-0050).

Private to the planning: the paste judges a block against the columns of the node it is aimed at.
"""

from typing import TYPE_CHECKING

from waterfall.core.planning.tree import LINE, TASK

if TYPE_CHECKING:
    from waterfall.core.history.interface import NodeColumn

# The columns of the facet task, in the order of ``NodeColumn``: the others are the estimate line's.
TASK_COLUMNS: tuple[NodeColumn, ...] = (
    "label",
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "physical_progress",
    "total_float",
    "is_critical",
    "started_on",
    "completed_on",
    "predecessors",
    "work_breakdown",
)
# The columns of a task that its execution writes, which ``setTaskProgress`` writes under
# ``remaining.write`` (EP-09): the others of ``TASK_COLUMNS`` are the planning's.
EXECUTION_COLUMNS: frozenset[str] = frozenset(("physical_progress", "started_on", "completed_on"))
# The columns of the estimate line, after its label, in the order of ``NodeColumn`` (EP-07).
LINE_COLUMNS: tuple[NodeColumn, ...] = (
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)
# The columns a block aimed at a node of a kind fills, by kind; the order of the refusals.
COLUMNS_OF: dict[str, tuple[NodeColumn, ...]] = {
    TASK: TASK_COLUMNS,
    LINE: ("label", *LINE_COLUMNS),
}
ALL_COLUMNS: tuple[NodeColumn, ...] = (*TASK_COLUMNS, *LINE_COLUMNS)
