# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk (WF-RIS-0060).

``getRiskOccurrenceReport`` (US-2620/L1), the report before the occurrence, and
``declareRiskOccurrence`` (US-2620/L2), the occurrence confirmed and handed to the worker, under
``risk_occurrence``.

Registered by the application, empty until US-2620 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["risks"])
