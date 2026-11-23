# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/imports.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1420 declares each operation it serves, with the
quality on its project each asks for besides.

A deposit asks for no permission: it writes nothing of any project, and only its author may open
an import of it. An import of a project is guarded by the visibility of the project alone
(US-2660/L1, #2473): the kind of an import is judged with the import itself (``Format.reading``,
``Format.permission``), its imports unknown to who does not consult the function of the kind
(404), so that an estimator reads and imports its estimate without reading the planning. The
permission of the kind and the quality of contributor, which an opening, an application, an
abandonment and a change of the rule of its durations (US-2000) ask for besides, are judged there
too, so that an application whose requester lost them refuses the import for good (WF-ARC-0100) —
the 403 the contract declares for these four (``BY_KIND``), which ``test_access_evaluation.py``
admits by their names.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "uploadFile": (),
    "listImports": (),
    "openImport": (),
    "getImport": (),
    "abandonImport": (),
    "applyImport": (),
    "setImportDurationRule": (),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "listImports": "consultation",
    "openImport": "consultation",
    "getImport": "consultation",
    "abandonImport": "consultation",
    "applyImport": "consultation",
    "setImportDurationRule": "consultation",
}
# The operations whose route asks for no permission and still refuse by a 403, because the
# exchanges judge the writing of the kind of the import and the quality of contributor with it.
# The reading of the kind refuses by the 404 of the project every operation above declares;
# ``listImports`` and ``getImport``, which write nothing, refuse by no 403 and are not here.
BY_KIND = {"openImport", "abandonImport", "applyImport", "setImportDurationRule"}
