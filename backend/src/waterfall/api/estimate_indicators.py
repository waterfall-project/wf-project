# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks.

``getEstimateIndicators`` and ``getMissingRates`` (US-1510).

Registered by the application, empty until US-1510 serves them (US-1490/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["estimate"])
