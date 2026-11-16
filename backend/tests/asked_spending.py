# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operation of ``api/spending.py`` asks for (EP-10, US-2050).

``test_access_evaluation.py`` gathers them; US-2050 declares the projection of spending, read under
the permission to consult the estimate, with the quality on its project it asks for besides.
"""

# The permission the operation asks for: the projection is read under that of the estimate.
ASKED: dict[str, tuple[str, ...]] = {
    "getProjectSpending": ("estimate.read",),
}
# The quality on its project the operation asks for, evaluated by ``RequiresProject``.
ON_PROJECT: dict[str, str] = {
    "getProjectSpending": "consultation",
}
