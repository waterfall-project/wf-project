# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the exchanges: the analysis and the application of an import, an export.

``import_analysis``, ``import_apply`` and ``export`` (WF-ARC-0090): the exchanges run each in the
one transaction of the task, through the format or the exporter of its kind; a refusal fails the
task with its code, nothing of the project written (EP-06, "Le worker"). The file of an import is
read from the bucket the settings name, under ``uploads/``.

The application judges its requester again as it stands when the task runs — its effective
permissions and its quality on the project, read now —: a permission withdrawn since the
confirmation refuses the import (WF-ARC-0100). The permissions are evaluated here, by the module
of the permissions, which sits above the exchanges.

Declared by US-1380/L1; US-1420/L1 fills the analysis and the application, US-1430/L2 the export.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.access_roles.interface import actor_of, require_project
from waterfall.core.exchanges.interface import run_analysis, run_apply, run_export
from waterfall.core.projects.interface import Viewer
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.tasks import Task


@dataclass(frozen=True, slots=True)
class ImportTasks:
    """The analysis and the application of an import, on the bucket their files are kept in."""

    files: Bucket

    @classmethod
    def of(cls, settings: ServiceSettings) -> ImportTasks:
        """Open the bucket of the backups the settings name, which keeps the files in transit."""
        return cls(Bucket.of_backups(settings))

    def analyse(self, session: Session, task: Task) -> Mapping[str, Any] | None:
        """Analyse the file of the import a task names, and keep its report."""
        return run_analysis(session, task, self.files)

    def apply(self, session: Session, task: Task) -> Mapping[str, Any] | None:
        """Apply the report of the import a task names, its requester judged as it stands now."""
        if task.requested_by is None:
            msg = "an import is applied for the account that confirmed it"
            raise ValueError(msg)
        actor = actor_of(session, task.requested_by)

        def judge(session: Session, project_id: UUID, permission: str) -> None:
            require_project(session, actor, project_id, permission)

        viewer = Viewer(actor.user_id, actor.permissions)
        return run_apply(session, task, self.files, viewer, judge)


def export(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Write the file of the export a task asks for, and give where it is kept."""
    return run_export(session, task)
