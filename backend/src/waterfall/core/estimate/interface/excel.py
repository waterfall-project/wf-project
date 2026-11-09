# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``estimate``: the workbook of an estimate (appendix B; US-1550).

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a workbook, analyses it against a structure
and applies its report, the exporter writes the estimate of a structure — XlsxWriter writes,
openpyxl reads (EP-07, "Le format Excel du devis"). ``sheet_name`` names a tab of a workbook from
a subproject (#2190), which EP-09 imports too.

Declared by US-1490/L1 and registered without effect (decision of 2026-11-08, #2370); the format
reads the header, analyses and applies a workbook from US-1550/L3: the header is read in the whole
file — a workbook is a zip, whose header no head of bytes holds —, by the reader of US-1550/L2
(``excel/reader.py``), the analysis is ``importing``'s, the application ``applying``'s. The export
raises ``NotImplementedError`` naming the story that fills it. ``sheet_name`` is written by
US-1550/L1 (``excel/names.py``), as the workbook (``excel/writer.py``).
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate import applying, importing
from waterfall.core.estimate.excel.names import sheet_name as named_sheet
from waterfall.core.estimate.excel.reader import check_header, read_workbook
from waterfall.core.exchanges.interface import LARGEST_FILE
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import ConflictError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import (
        ExportedFile,
        ExportOrder,
        ImportScope,
        ImportTarget,
    )
    from waterfall.platform.audit import Act

# The bytes of a file the header is read in: the whole file, at most what a deposit holds.
HEADER_LENGTH = LARGEST_FILE
# The states of a project whose main structure an estimate is imported in (WF-INTF-0100; C-358).
BEFORE_IN_PROGRESS = ("created", "pricing")
PROJECT_BEFORE_IN_PROGRESS = "project_before_in_progress"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"


class EstimateFormat:
    """The format of the workbook of an estimate, as the exchanges ask it (``Format``).

    It writes a structure of the current revision, under the permission to write the estimate.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "structure"
    permission = "estimate.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse a file that is not the workbook of an estimate of a known version (422).

        ``FILE_FORMAT_UNREADABLE``, ``expected_format`` and ``expected_version`` (WF-INTF-0070).
        """
        del session
        check_header(head)

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an estimate imported on the main structure of a project In progress (409).

        ``project_before_in_progress``, the condition the main structure names at the entry of its
        estimate (WF-INTF-0100; C-358); the project read under the lock its caller holds. A
        project without a revision yet aims at the main structure its import creates.
        """
        project_id, structure_id = target.project_id, target.structure_id
        if (
            structure_id is not None
            and not structure_facts(session, project_id, structure_id, lock=False).is_main
        ):
            return
        if project_facts(session, project_id).state not in BEFORE_IN_PROGRESS:
            missing = {"missing_condition": PROJECT_BEFORE_IN_PROGRESS}
            raise ConflictError(STATE_FORBIDS_OPERATION, missing)

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a workbook against a structure, writing nothing (``importing``)."""
        read = read_workbook(content)
        held = importing.aimed(session, target)
        return importing.report_of(held, read, importing.analyse(session, held, read))

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a workbook into a structure, judged again (``applying``)."""
        applying.apply(session, target, content, report, act)


class EstimateExporter:
    """The exporter of the workbook of an estimate, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the estimate of a structure in a workbook."""
        msg = "export is filled by US-1550"
        raise NotImplementedError(msg)


def sheet_name(label: str, taken: Iterable[str] = ()) -> str:
    """Name a tab of a workbook from a label, as Excel admits it (#2190).

    The characters Excel refuses are replaced, the name is cut to 31 UTF-16 units, and it differs
    from every name of ``taken`` without regard to case, by a suffix `` (2)``, `` (3)``…
    """
    return named_sheet(label, taken)


ESTIMATE_FORMAT = EstimateFormat()
ESTIMATE_EXPORTER = EstimateExporter()
