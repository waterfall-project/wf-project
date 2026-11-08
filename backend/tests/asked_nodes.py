# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/nodes.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1380 declares each operation it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "planning.read"
CHANGE = "planning.write"

# The permissions each operation asks for, in the order they are evaluated: the tree is read by
# the holder of the permission to consult the planning, written by the holder of that to write it,
# the command ``edit_planning`` of the structure (US-1380/L2).
ASKED: dict[str, tuple[str, ...]] = {
    "listNodes": (CONSULT,),
    "createNode": (CONSULT, CHANGE),
    "updateTaskFacet": (CONSULT, CHANGE),
    "getComputedValueDependencies": (CONSULT,),
    "resolveRowNumber": (CONSULT,),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "listNodes": "consultation",
    "createNode": "contributor",
    "updateTaskFacet": "contributor",
    "getComputedValueDependencies": "consultation",
    "resolveRowNumber": "consultation",
}
