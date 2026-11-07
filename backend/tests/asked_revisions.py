# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/revisions.py`` ask for: the revisions and their structures.

``test_access_evaluation.py`` gathers them; US-0960 and US-0970 declare each operation they serve,
with the quality on its project each asks for besides (``ON_PROJECT``, declared by US-0910/L2).
"""

CONSULT = "revisions.read"

# The permissions each operation asks for, in the order they are evaluated: the history, a
# revision and its structures are read by the holder of the permission to consult the revisions,
# a revision is opened by the holder of the permission to manage them, and marked or abandoned by
# the holder of the permission of that action, a structuring action (WF-ADM-0100).
ASKED: dict[str, tuple[str, ...]] = {
    "listRevisions": (CONSULT,),
    "createRevision": (CONSULT, "revisions.write"),
    "getRevision": (CONSULT,),
    "abandonRevision": (CONSULT, "revision_abandon"),
    "markRevision": (CONSULT, "revision_mark"),
    "listCostStructures": (CONSULT,),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110, WF-PRJ-0060).
ON_PROJECT: dict[str, str] = {
    "listRevisions": "consultation",
    "createRevision": "contributor",
    "getRevision": "consultation",
    "abandonRevision": "project_manager",
    "markRevision": "project_manager",
    "listCostStructures": "consultation",
}
