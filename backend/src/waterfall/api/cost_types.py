# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures and the categories of cost (FBS-3.1).

``listCostTypes``, ``createCostType``, ``updateCostType``, ``setCostTypeActivation`` and the
same four for the categories.

Registered by the application, empty until US-0820 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
