# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/timelines.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1400 declares each operation it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "planning.read"
CHANGE = "planning.write"

# The permissions each operation asks for, in the order they are evaluated: the timelines are read
# by the holder of the permission to consult the planning, written by the holder of that to write
# it, as the command ``manage_timelines`` of the project is (WF-PLA-0140).
ASKED: dict[str, tuple[str, ...]] = {
    "listTimelines": (CONSULT,),
    "createTimeline": (CONSULT, CHANGE),
    "deleteTimeline": (CONSULT, CHANGE),
    "setNodeTracking": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "listTimelines": "consultation",
    "createTimeline": "contributor",
    "deleteTimeline": "contributor",
    "setNodeTracking": "contributor",
}
