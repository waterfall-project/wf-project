# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format ``actual_costs``: the extraction of the actual costs of the ERP (FLX-07; US-1610).

Registered at the import of the interface in the registry of the exchanges (``register_format``):
the format reads the header of an extraction against the mapping of the cost settings, analyses
its lines against those of the project — the WBS element, the document and its item, the date, the
amount, the columns kept — and applies its report, an entry of the log and the lines inserted or
updated on their document and item (EP-09, "Les coûts réels"). An import of the actual costs writes
in the project, under the permission to write its actual costs; it aims at no structure.

Declared by US-1580/L1; US-1610/L1 judges an import on the state of its project and the mapping,
reads the header at the opening (``extraction``) and analyses (``analysing``); US-1610/L2 applies.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.cost_settings.interface import read_actual_cost_mapping
from waterfall.core.costs import analysing
from waterfall.core.costs.extraction import HEADER_ROW, read_header, sheet_rows
from waterfall.core.exchanges.interface import LARGEST_FILE
from waterfall.core.projects.interface import no_background_task_running, project_facts
from waterfall.platform.errors import ConflictError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ImportScope, ImportTarget
    from waterfall.platform.audit import Act

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
# The conditions of ``ProjectCommand.import_actual_costs``, in its order (WF-REF-0190; D-04).
PROJECT_IN_PROGRESS = "project_in_progress"
NO_BACKGROUND_TASK_RUNNING = "no_background_task_running"
ACTUAL_COST_MAPPING_COMPLETE = "actual_cost_mapping_complete"
IN_PROGRESS = "in_progress"
# The bytes of a file the header is read in: the whole file, at most what a deposit holds. A
# workbook is a zip, whose directory is at its end: no head of bytes holds the header. openpyxl,
# in read-only mode, inflates only the first row of the first tab.
HEADER_LENGTH = LARGEST_FILE


def _refused(condition: str, **params: Any) -> ConflictError:
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition, **params})


class ActualCostsFormat:
    """The format of an extraction of the actual costs, as the exchanges ask it (``Format``).

    It writes in the project, under the permission to write its actual costs.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "project"
    permission = "actual_costs.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse a file that is no extraction, or lacks a required column of the mapping (422).

        ``FILE_FORMAT_UNREADABLE``, ``expected_format`` ``actual_costs``, and ``missing_columns``
        for the columns the headers of its first tab do not name (WF-INTF-0070, WF-REF-0190).

        Before the header, a mapping whose required columns lack a label is refused (409
        ``actual_cost_mapping_complete``, ``params.columns`` those, in the order of the mapping;
        WF-REF-0190): the exchanges ask ``read_header`` at the opening only, after ``judge``, so
        that the order of the conditions stays that of ``ProjectCommand.import_actual_costs``.
        An import analysed is applied as it was analysed, whatever the mapping became.
        """
        missing = read_actual_cost_mapping(session).missing_columns
        if missing:
            raise _refused(ACTUAL_COST_MAPPING_COMPLETE, columns=list(missing))
        rows = sheet_rows(head, max_row=HEADER_ROW)
        read_header(session, rows[0] if rows else ())

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of the actual costs on its project or its tasks (409).

        In the order of ``ProjectCommand.import_actual_costs``, after the terminal project the
        exchanges refuse: a project not In progress (``project_in_progress``), then a task of the
        background that writes in it, but the application that asks
        (``no_background_task_running``). The mapping is not judged here, which the application
        replays: an import analysed is applied as it was analysed (``read_header`` judges it at the
        opening; WF-REF-0190). The project is read under the lock its caller holds.
        """
        project_id = target.project_id
        if project_facts(session, project_id).state != IN_PROGRESS:
            raise _refused(PROJECT_IN_PROGRESS)
        if not no_background_task_running(session, project_id, target.running):
            raise _refused(NO_BACKGROUND_TASK_RUNNING)

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of an extraction against the lines of the project, writing nothing."""
        return analysing.analyse(session, target.project_id, content)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of an extraction: the entry of the log, then the lines."""
        msg = "apply is filled by US-1610/L2"
        raise NotImplementedError(msg)


ACTUAL_COSTS_FORMAT = ActualCostsFormat()
