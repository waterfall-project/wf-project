# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution, by column: the Kanban.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1590/L2 writes its tests here ("Les tests du back"). The socle fixes the result EP-10 reads.
"""

from annotationlib import Format, get_annotations
from dataclasses import fields

from waterfall.core.estimate.interface import (
    KanbanTask,
    NotStartedTask,
    StartableTasks,
    startable_tasks,
)


def test_the_board_answers_three_columns_of_whole_nodes_with_their_gestures() -> None:
    # What EP-10 reads from the socle on (EP-09, "Ce que le cadrage laisse à EP-10"): the result is
    # fixed before US-1590/L2 fills it.
    assert get_annotations(startable_tasks, format=Format.FORWARDREF)["return"] is StartableTasks
    assert [field.name for field in fields(StartableTasks)] == [
        "not_started",
        "started",
        "completed",
    ]
    assert [field.name for field in fields(KanbanTask)] == ["node", "available_commands"]
    assert [field.name for field in fields(NotStartedTask)] == [
        "node",
        "available_commands",
        "predecessors_completed",
    ]
