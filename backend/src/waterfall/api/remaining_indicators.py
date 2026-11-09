# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit of a project (WF-RAE-0020).

``getRemainingIndicators`` (US-1600), under ``remaining.read``.

Registered by the application, empty until US-1600 serves it (US-1580/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["remaining"])
