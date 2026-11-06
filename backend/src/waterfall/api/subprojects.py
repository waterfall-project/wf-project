# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (WF-PRJ-0050).

``listSubprojects``, ``createSubproject``, ``updateSubproject`` and ``deleteSubproject``.

Registered by the application, empty until US-0940 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["projects"])
