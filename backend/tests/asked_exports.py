# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/exports.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1430 and US-1440 declare each operation they
serve, with the quality on its project each asks for besides.
"""

CONSULT = "planning.read"

# The permissions each operation asks for, in the order they are evaluated: an export is a matter
# of consultation, the route asking for the permission to consult the planning and the command
# ``export_*`` of the kind, judged on the revision, for that of its function (WF-CYC-0110); the
# result of a task is read by the account that asked for it, with no permission (WF-ARC-0090).
ASKED: dict[str, tuple[str, ...]] = {
    "requestExport": (CONSULT,),
    "getBackgroundTaskResult": (),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {"requestExport": "consultation"}
