# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the actual costs of a project, read and excluded (WF-CRE-0030, WF-CRE-0040).

``listActualCosts`` (US-1620/L1), under ``actual_costs.read``; ``setActualCostTrackedScope``
(US-1620/L1), under the quality of contributor and ``cost_line_exclude``.

Registered by the application, empty until US-1620 serves it (US-1580/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["actual-costs"])
