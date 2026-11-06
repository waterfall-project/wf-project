# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (WF-PRJ-0050).

Listed, created, changed and deleted for good while nothing cites them, each with its commands;
their code unique in the project, never one of the two names Waterfall gives its own tabs (#1502).

Declared by US-0910/L1, without effect: US-0940 fills it; ``load_subprojects`` writes those of the
witness.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def list_subprojects(session: Session, project_id: UUID) -> None:
    """List the subprojects of a project, with their commands (``listSubprojects``)."""


def create_subproject(session: Session, project_id: UUID, act: Act) -> None:
    """Create a subproject (``createSubproject``)."""


def update_subproject(
    session: Session, project_id: UUID, subproject_id: UUID, lock_version: int, act: Act
) -> None:
    """Change a subproject at the version read (``updateSubproject``)."""


def delete_subproject(
    session: Session, project_id: UUID, subproject_id: UUID, lock_version: int, act: Act
) -> None:
    """Delete a subproject that nothing cites (``deleteSubproject``)."""


def load_subprojects(session: Session, project_id: UUID, act: Act) -> None:
    """Write the subprojects of a project of the witness, as it imposes them."""
