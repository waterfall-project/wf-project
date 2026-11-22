# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How many projects the platform holds, which a backup counts and its test compares (US-2930).

The manifest of a backup says it, and the test of a restoration counts them again in the database
restored: a number that differs fails the test (WF-EXP-0060).
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.projects.tables import Project

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def count_projects(session: Session) -> int:
    """Give the number of the projects of the platform, whatever their state."""
    return session.scalar(select(func.count()).select_from(Project)) or 0
