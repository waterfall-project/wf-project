# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects (FBS-4.2).

``listProjects``, ``createProject``, ``getProject`` and ``updateProject``.

Registered by the application, empty until US-0920/L1 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["projects"])
