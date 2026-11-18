# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks and the coverage of a project (WF-RIS-0050).

``getProjectRiskCoverage`` (US-2610/L1), under ``risks.read``.

Registered by the application, empty until US-2610 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
