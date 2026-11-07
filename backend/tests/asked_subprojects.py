# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/subprojects.py`` ask for: the subprojects of a project.

``test_access_evaluation.py`` gathers them; US-0940 declares each operation it serves,
with the quality on its project each asks for besides (``ON_PROJECT``, declared by US-0910/L2).
"""

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"

# The permissions each operation asks for, in the order they are evaluated: the subprojects are
# read by the holder of the permission to consult the settings of a project, written by the holder
# of that to change them, as the command ``update`` of the project is (WF-PRJ-0050, WF-PRJ-0060).
ASKED: dict[str, tuple[str, ...]] = {
    "listSubprojects": (CONSULT,),
    "createSubproject": (CONSULT, CHANGE),
    "updateSubproject": (CONSULT, CHANGE),
    "deleteSubproject": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110, WF-PRJ-0060).
ON_PROJECT: dict[str, str] = {
    "listSubprojects": "consultation",
    "createSubproject": "project_manager",
    "updateSubproject": "project_manager",
    "deleteSubproject": "project_manager",
}
