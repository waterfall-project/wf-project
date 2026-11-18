# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/project_indicators.py`` ask for (EP-10).

``test_access_evaluation.py`` gathers them; US-1660/L3 declares the operation it serves, under
``project_indicators.read``, with the quality on its project it asks for besides: whoever consults
the project reads its indicators.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {"getProjectIndicators": ("project_indicators.read",)}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {"getProjectIndicators": "consultation"}
