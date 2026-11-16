# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The earned value indicators of a project (WF-IND-0010 to WF-IND-0080).

``getProjectIndicators`` (US-1660/L3: the current day; US-1670/L2: a marked revision named, a
date), under ``project_indicators.read``.

Registered by the application, empty until US-1660/L3 serves it (US-1660/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["indicators"])
