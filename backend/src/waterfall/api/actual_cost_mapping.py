# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mapping of the extraction of the actual costs (FBS-3.1).

``getActualCostMapping`` and ``setActualCostMapping`` (WF-REF-0190).

Registered by the application, empty until US-0870 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
