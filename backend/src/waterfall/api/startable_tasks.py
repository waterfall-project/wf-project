# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution of a project, by column: the Kanban (WF-RAE-0030).

``listStartableTasks`` (US-1590/L2), under ``remaining.read``; the gesture of a card is
``setTaskProgress``, which stays with the router of the progress of the planning.

Registered by the application, empty until US-1590 serves it (US-1580/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["remaining"])
