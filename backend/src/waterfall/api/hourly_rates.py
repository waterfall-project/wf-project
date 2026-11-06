# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates of the categories of labour (FBS-3.1).

``getHourlyRateGrid``, ``listHourlyRates`` and ``setHourlyRate``.

Registered by the application, empty until US-0830 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
