# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (§3.3.2).

``getProjectNextState``, ``exitProject`` and ``listProjectStateTransitions`` (US-0980/L1);
``designateReferenceRevision`` (US-0980/L2).

Registered by the application, empty until US-0980 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["projects"])
