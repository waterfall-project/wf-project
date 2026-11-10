# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The log of the imports of the actual costs of a project (WF-CRE-0050).

``listCostImports`` (US-1610/L2), under ``actual_costs.read``; the opening, the application and the
abandonment of an import stay with the router of the exchanges, which asks the format of its kind.

Registered by the application, empty until US-1610 serves it (US-1580/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["actual-costs"])
