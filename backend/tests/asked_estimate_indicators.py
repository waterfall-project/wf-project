# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/estimate_indicators.py`` ask for (EP-07).

``test_access_evaluation.py`` gathers them; US-1510 declares each operation it serves, with the
quality on its project each asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated: the indicators and the
# rates a revision lacks are read by whoever may consult the estimate (US-1510).
ASKED: dict[str, tuple[str, ...]] = {
    "getEstimateIndicators": ("estimate.read",),
    "getMissingRates": ("estimate.read",),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "getEstimateIndicators": "consultation",
    "getMissingRates": "consultation",
}
