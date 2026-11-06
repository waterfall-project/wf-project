# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of a project and their kind (WF-PRJ-0060).

``listContributors``, ``setContributors`` and ``listContributorSuggestions``.

Registered by the application, empty until US-0930 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["projects"])
