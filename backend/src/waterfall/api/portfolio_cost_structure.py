# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of the costs of the portfolio (WF-PTF-0080).

``getPortfolioCostStructure`` (US-2720), under ``portfolio_cost_structure.read``. A view of the
portfolio is guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

Registered by the application, empty until US-2720 serves it (US-2670/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["portfolio"])
