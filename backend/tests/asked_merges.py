# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/merges.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2560 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "revisions.read"

# The permissions each operation asks for, in the order they are evaluated: the report of a merge
# is read by whoever consults the revisions, without a 403, as any read of the project (US-2560/L1);
# the merge, a structuring action of its own permission, by a project manager (US-2560/L2).
ASKED: dict[str, tuple[str, ...]] = {
    "getStructureMergeReport": (CONSULT,),
    "mergeCostStructure": (CONSULT, "structure_merge"),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "getStructureMergeReport": "consultation",
    "mergeCostStructure": "project_manager",
}
