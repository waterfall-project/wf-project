# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register and the matrix of the risks of a project (WF-RIS-0040).

``listRisks`` (US-2600/L1) and ``getProjectRiskMatrix`` (US-2600/L2), under ``risks.read``.

Registered by the application, empty until US-2600 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
