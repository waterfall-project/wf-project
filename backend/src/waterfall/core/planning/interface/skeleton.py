# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The skeleton of a planning, engendered from the work breakdown of its project.

``generatePlanningSkeleton``, under the command ``generate_skeleton`` of the project (EP-06,
US-1460).

Declared by US-1380/L1; US-1460 fills it, and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def generate_skeleton(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Engender the tasks of a structure from the work breakdown of its project."""
    msg = "generate_skeleton is filled by US-1460"
    raise NotImplementedError(msg)
