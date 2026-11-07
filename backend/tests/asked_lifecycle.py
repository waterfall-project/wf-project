# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/lifecycle.py`` ask for: the cycle of life of a project.

``test_access_evaluation.py`` gathers them; US-0980 declares each operation it serves,
with the quality on its project each asks for besides (``ON_PROJECT``, declared by US-0910/L2).
"""

CONSULT = "lifecycle.read"

# The permissions each operation asks for, in the order they are evaluated: the next state and the
# transitions are read by the holder of the permission to consult the cycle of life, an exit is
# declared by the holder of the permission of its own, an irreversible action (WF-ADM-0100).
ASKED: dict[str, tuple[str, ...]] = {
    "getProjectNextState": (CONSULT,),
    "listProjectStateTransitions": (CONSULT,),
    "exitProject": (CONSULT, "project_exit"),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110, WF-PRJ-0060).
ON_PROJECT: dict[str, str] = {
    "getProjectNextState": "consultation",
    "listProjectStateTransitions": "consultation",
    "exitProject": "project_manager",
}
