# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution of a project, by column: the Kanban (WF-RAE-0030).

``listStartableTasks`` (US-1590/L2), under ``remaining.read``; the gesture of a card is
``setTaskProgress``, which stays with the router of the progress of the planning. The gestures a
card lists are those of the caller: none without ``remaining.write``, nor on a terminal project.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.nodes import node_body
from waterfall.api.projects import viewer_of
from waterfall.core.estimate.interface import KanbanTask, NotStartedTask, startable_tasks

router = APIRouter(tags=["remaining"])

CONSULT = "remaining.read"


def _card(card: KanbanTask) -> dict[str, Any]:
    """Write a card as the contract does: the node whole, and the gestures it lists."""
    return {
        **node_body(card.node),
        "available_commands": [
            {
                "command": each.command,
                "is_available": each.is_available,
                "missing_conditions": list(each.missing_conditions),
                "progress": each.progress,
            }
            for each in card.available_commands
        ],
    }


def _waiting(card: NotStartedTask) -> dict[str, Any]:
    """Write a card of a task not started: the gestures, and whether its predecessors are done."""
    return {**_card(card), "predecessors_completed": card.predecessors_completed}


@router.get(
    "/projects/{project_id}/remaining-indicators/startable-tasks",
    operation_id="listStartableTasks",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_startable_tasks(
    project_id: UUID, session: Transaction, actor: Acting
) -> dict[str, list[dict[str, Any]]]:
    """Give the tasks of the main structure of the current revision by state, with their cards."""
    read = startable_tasks(session, project_id, viewer_of(actor))
    return {
        "not_started": [_waiting(each) for each in read.not_started],
        "started": [_card(each) for each in read.started],
        "completed": [_card(each) for each in read.completed],
    }
