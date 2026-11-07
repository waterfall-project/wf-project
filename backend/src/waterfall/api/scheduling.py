# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predecessors of a task and the date the planning of a structure starts on.

``setPredecessors`` and ``updateCostStructure`` (US-1390/L2).

Registered by the application, empty until US-1390 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
