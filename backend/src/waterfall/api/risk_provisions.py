# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision of an identified risk changed (WF-RIS-0010).

``updateRiskProvision`` (US-2580/L1), under ``risks.write``.

Registered by the application, empty until US-2580 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
