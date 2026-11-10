# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``remaining``: the workbook of a remaining to commit (US-1630).

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a workbook « Reste à engager » (FLX-05),
analyses it by lineage against the lines of the main structure and applies its report through the
re-estimation; the exporter writes the remaining to commit of a revision (FLX-06) — XlsxWriter
writes, openpyxl reads, in ``remaining/excel/`` (EP-09, "Le format Excel du reste à engager").

Declared by US-1580/L1 and registered without effect, as the socle of EP-07 registered the format
``estimate`` (#2370). US-1630/L3 fills the format: the header is read in the whole file — a workbook
is a zip, whose directory is at its end — by the reader of US-1630/L2 (``remaining/excel/reader``),
the analysis is ``remaining/analysing``'s, the application ``remaining/applying``'s, on the workbook
the preparation read before any lock (#2582). An import of a remaining to commit writes the main
structure of a project In progress (``ProjectCommand.import_remaining``, ``project_in_progress``).
The export is filled by US-1630/L4: ``exporting`` reads the remaining to commit of the structure of
the order, the writer of US-1630/L1 (``remaining/excel/writer``) turns it into the workbook, under
the tab names the analysis reads them by (``layout.tab_names``).
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate import importing
from waterfall.core.estimate.interface.remaining_indicators import remaining_indicators
from waterfall.core.estimate.remaining import analysing, applying, exporting
from waterfall.core.estimate.remaining.excel.reader import check_header, read_remaining_workbook
from waterfall.core.estimate.remaining.excel.writer import write_workbook
from waterfall.core.exchanges.interface import LARGEST_FILE, ExportedFile
from waterfall.core.projects.interface import project_facts
from waterfall.platform.database import utc_now
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.remaining.excel.reader import RemainingRead
    from waterfall.core.exchanges.interface import (
        ExportOrder,
        ImportScope,
        ImportTarget,
    )
    from waterfall.platform.audit import Act

# The bytes of a file the header is read in: the whole file, at most what a deposit holds — a
# workbook is a zip, whose directory is at its end.
HEADER_LENGTH = LARGEST_FILE
# The phase a remaining to commit is imported in (WF-RAE-0040; ``ProjectCommand.import_remaining``).
IN_PROGRESS = "in_progress"
PROJECT_IN_PROGRESS = "project_in_progress"
MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class RemainingFormat:
    """The format of the workbook of a remaining to commit, as the exchanges ask it (``Format``).

    It writes the main structure of the current revision, under the permission to write the
    remaining to commit.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "structure"
    permission = "remaining.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse a file that is not the workbook of a remaining of a known version (422).

        ``FILE_FORMAT_UNREADABLE``, ``expected_format`` ``remaining`` and ``expected_version``
        (WF-INTF-0070).
        """
        del session
        check_header(head)

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse a remaining to commit imported on a project not In progress (409).

        ``project_in_progress``, the phase of ``ProjectCommand.import_remaining`` (WF-RAE-0040), at
        the opening, at the application and when its task runs; the project read under the lock
        its caller holds.
        """
        if project_facts(session, target.project_id).state != IN_PROGRESS:
            missing = {"missing_condition": PROJECT_IN_PROGRESS}
            raise ConflictError(STATE_FORBIDS_OPERATION, missing)

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a workbook against the main structure, writing nothing."""
        read = read_remaining_workbook(content)
        held = importing.aimed(session, target)
        return analysing.report_of(held, read, analysing.analyse(session, held, read))

    def prepare(self, content: bytes) -> RemainingRead:
        """Read a whole workbook of a remaining to commit, before any lock."""
        return read_remaining_workbook(content)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        prepared: RemainingRead,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a workbook read into the main structure, through the re-estimate."""
        applying.apply(session, target, prepared, report, act)


class RemainingExporter:
    """The exporter of the workbook of a remaining to commit, as the exchanges ask it."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the remaining to commit of a structure in a workbook, in the task's transaction.

        The amounts of the headers are the indicators' of the revision at the instant of the
        export (``remaining_indicators``); the review date is the order's, the day of the request
        when it names none. The file is named after the project and the version of the revision.
        """
        at = utc_now()
        indicators = remaining_indicators(session, order.project_id, order.revision_id, at)
        balances = {each.key: (each.budget, each.actual_cost) for each in indicators.by_subproject}
        book, name = exporting.remaining_of(session, order, balances, at)
        return ExportedFile(write_workbook(book), MEDIA_TYPE, name)


REMAINING_FORMAT = RemainingFormat()
REMAINING_EXPORTER = RemainingExporter()
