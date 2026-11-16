# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a project: the cumulative costs and the earned value (WF-IND-0100, WF-IND-0110).

``getCostCurve`` and ``getEarnedValueCurves`` (US-1690/L2: the current day; US-1690/L3: a marked
revision), under ``project_indicators.read``.

Registered by the application, empty until US-1690 serves them (US-1660/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["indicators"])
