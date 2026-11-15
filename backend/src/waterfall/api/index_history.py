# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evolution of the indices of a project (WF-IND-0130).

``getIndexHistory`` (US-1700), under ``project_indicators.read``.

Registered by the application, empty until US-1700 serves it (US-1660/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["indicators"])
