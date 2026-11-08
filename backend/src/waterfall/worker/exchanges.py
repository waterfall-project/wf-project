# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the exchanges: the analysis and the application of an import, an export.

``import_analysis``, ``import_apply`` and ``export`` (WF-ARC-0090): the exchanges run each in the
one transaction of the task, through the format or the exporter of its kind; a refusal fails the
task with its code, nothing written (EP-06, "Le worker").

Declared by US-1380/L1; US-1420/L1 fills the analysis and the application, US-1430/L2 the export.
"""

from typing import TYPE_CHECKING

from waterfall.core.exchanges.interface import run_analysis, run_apply, run_export

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task


def analyse(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Analyse the file of the import a task names, and keep its report."""
    return run_analysis(session, task)


def apply(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Apply the report of the import a task names."""
    return run_apply(session, task)


def export(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Write the file of the export a task asks for, and give where it is kept."""
    return run_export(session, task)
