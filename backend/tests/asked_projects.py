# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/projects.py`` ask for: the projects.

``test_access_evaluation.py`` gathers them; US-0920/L1 declares each operation it serves,
with the quality on its project each asks for besides (``ON_PROJECT``, declared by US-0910/L2).
"""

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"

# The permissions each operation asks for, in the order they are evaluated: a project is created
# by the holder of the permission to create one, listed and read by the holder of the permission
# to consult the settings of a project, changed by the holder of that to change them.
ASKED: dict[str, tuple[str, ...]] = {
    "listProjects": (CONSULT,),
    "createProject": ("project_create",),
    "getProject": (CONSULT,),
    "updateProject": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110, WF-PRJ-0060).
ON_PROJECT: dict[str, str] = {"getProject": "consultation", "updateProject": "project_manager"}
