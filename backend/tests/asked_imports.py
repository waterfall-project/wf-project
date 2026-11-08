# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/imports.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1420 declares each operation it serves, with the
quality on its project each asks for besides.

A deposit asks for no permission: it writes nothing of any project, and only its author may open
an import of it. An import of a project is guarded by the reading of the planning, the leaf the
exchanges are of (FBS-4.3.4); the permission of its kind and the quality of contributor, which an
opening, an application and an abandonment ask for besides, are judged with the import itself
(``Format.permission``), so that an application whose requester lost them refuses the import for
good (WF-ARC-0100) — the 403 the contract declares for these three.
"""

CONSULT = "planning.read"

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "uploadFile": (),
    "listImports": (CONSULT,),
    "openImport": (CONSULT,),
    "getImport": (CONSULT,),
    "abandonImport": (CONSULT,),
    "applyImport": (CONSULT,),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "listImports": "consultation",
    "openImport": "consultation",
    "getImport": "consultation",
    "abandonImport": "consultation",
    "applyImport": "consultation",
}
