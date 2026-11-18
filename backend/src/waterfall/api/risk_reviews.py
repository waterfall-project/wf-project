# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reviews of a risk, the changes of its state and its deletion (WF-RIS-0020).

``reviewRisk``, ``listRiskReviews`` and ``deleteRisk`` (US-2590/L1), under ``risks.read`` and
``risks.write``.

Registered by the application, empty until US-2590 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
