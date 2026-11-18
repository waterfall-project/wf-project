# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared, read and renamed (WF-RIS-0010, WF-RIS-0020).

``createRisk``, ``getRisk`` and ``updateRisk`` (US-2570/L1), under ``risks.read`` and
``risks.write``.

Registered by the application, empty until US-2570 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
