# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/skeleton.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1460 declares each operation it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "planning.read"
CHANGE = "planning.write"

# The permissions each operation asks for, in the order they are evaluated: the skeleton is written
# by the holder of the permission to write the planning, the command ``generate_skeleton`` of the
# revision (US-1460).
ASKED: dict[str, tuple[str, ...]] = {
    "generatePlanningSkeleton": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "generatePlanningSkeleton": "contributor",
}
