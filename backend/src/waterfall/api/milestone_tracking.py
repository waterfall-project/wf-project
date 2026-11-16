# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time/time diagram of a project (WF-IND-0090).

``getMilestoneTracking`` (US-1710), under ``project_indicators.read``.

Registered by the application, empty until US-1710 serves it (US-1660/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["indicators"])
