# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/indicator_curves.py`` ask for (EP-10).

``test_access_evaluation.py`` gathers them; US-1690/L2 declares each operation it serves, under
``project_indicators.read``, with the quality on its project each asks for besides: whoever
consults the project reads its curves.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "getCostCurve": ("project_indicators.read",),
    "getEarnedValueCurves": ("project_indicators.read",),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "getCostCurve": "consultation",
    "getEarnedValueCurves": "consultation",
}
