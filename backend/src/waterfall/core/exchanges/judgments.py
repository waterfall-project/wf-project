# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What an import aims at, and the state of its project it is judged on, private to the module.

One judgment serves the opening, the application and its task (EP-06, "L'import en deux temps"):
a terminal project first; then, for an import that writes in the current revision, a task of the
background that writes in it or freezes it, and the permission to create the revision the import
would create — a 409 that names the condition, and not a 403 (``ProjectCommand.import_*``, I-04,
#1792). The conditions of a kind, those of its format, come after.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Literal

from waterfall.core.projects.interface import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    no_background_task_running,
)
from waterfall.platform.errors import ConflictError

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import ProjectFacts, Viewer

# What an import of a kind writes: a structure of the current revision, created if need be — a
# planning, an estimate, a remaining to commit (WF-INTF-0090) —, or rows of the project alone,
# outside any revision, over a period — the actual costs (WF-CRE-0010, WF-CRE-0050).
type ImportScope = Literal["structure", "project"]
# What judges the permission an import of a kind asks of an account on a project, and the quality
# of contributor a write asks for besides: it lets pass, or raises the refusal (403, 404).
type Judge = Callable[[Session, UUID, str], None]

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
NO_BACKGROUND_TASK_RUNNING = "no_background_task_running"
MAY_CREATE_REVISION = "may_create_revision"
# The conditions an application lacks for a while, which refuse it and leave the import awaiting
# its decision, its file kept: a background task ends, a permission is granted (WF-ARC-0100,
# #2475). The others refuse it for good.
PASSING = (NO_BACKGROUND_TASK_RUNNING, MAY_CREATE_REVISION)
# Who may create the revision an import creates (WF-INTF-0090).
REVISIONS_WRITE = "revisions.write"
# How long a report awaits its decision once analysed (WF-ARC-0100).
REPORT_LIFETIME = timedelta(hours=24)
# The keys of the payload of the tasks of an import: the import, the revision its analysis reads.
IMPORT_KEY = "import_id"
REVISION_KEY = "revision_id"


@dataclass(frozen=True, slots=True)
class ImportTarget:
    """The structure an import aims at, and its revision; neither for an import of the project.

    For the analysis, the revision is the current one, or the last marked one, whose copy the
    application creates; ``None`` both when the project has no revision yet, the application
    creating its first. For the application, the current revision, and its structure.
    """

    project_id: UUID
    revision_id: UUID | None
    structure_id: UUID | None


def refused(condition: str) -> ConflictError:
    """Refuse an operation of an import for a condition it lacks (409)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})


@dataclass(frozen=True, slots=True)
class Standing:
    """What an import is judged on: its project, as read under its lock, and what it writes."""

    project_id: UUID
    facts: ProjectFacts
    scope: ImportScope


def judge_state(
    session: Session, standing: Standing, viewer: Viewer, running: UUID | None = None
) -> None:
    """Refuse an import on the state of its project, read under its lock, in the contract's order.

    ``viewer`` is who would create the revision; ``running`` the task of the application that
    asks, which suspends no write of its own.
    """
    facts = standing.facts
    if facts.state in TERMINAL:
        raise refused(PROJECT_NOT_TERMINAL)
    if standing.scope != "structure":
        return
    if not no_background_task_running(session, standing.project_id, running):
        raise refused(NO_BACKGROUND_TASK_RUNNING)
    if facts.current_revision_id is None and REVISIONS_WRITE not in viewer.permissions:
        raise refused(MAY_CREATE_REVISION)
