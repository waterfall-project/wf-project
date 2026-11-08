# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``estimate``: the workbook of an estimate (appendix B; US-1550).

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a workbook, analyses it against a structure
and applies its report, the exporter writes the estimate of a structure — XlsxWriter writes,
openpyxl reads (EP-07, "Le format Excel du devis"). ``sheet_name`` names a tab of a workbook from
a subproject (#2190), which EP-09 imports too.

Declared by US-1490/L1 and registered without effect (decision of 2026-11-08, #2370): the format
refuses every head as a file it does not recognise (422 ``FILE_FORMAT_UNREADABLE``), as when no
format served the kind, so that an import of an estimate never passes before US-1550; the methods
it never reaches, the export and ``sheet_name`` raise ``NotImplementedError`` naming US-1550.
"""

from typing import TYPE_CHECKING, Any

from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import (
        ExportedFile,
        ExportOrder,
        ImportScope,
        ImportTarget,
    )
    from waterfall.platform.audit import Act

FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
# The bytes of the head of a file the header is read in, which US-1550 fixes.
HEADER_LENGTH = 4096


class EstimateFormat:
    """The format of the workbook of an estimate, as the exchanges ask it (``Format``).

    It writes a structure of the current revision, under the permission to write the estimate.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "structure"
    permission = "estimate.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse the head of a file that is not the workbook of an estimate: every one yet."""
        del session, head
        raise UnprocessableError(FILE_FORMAT_UNREADABLE, {"expected_format": "estimate"})

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of an estimate on the state of its project: none until US-1550."""
        del session, target

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a workbook against a structure, writing nothing."""
        msg = "analyse is filled by US-1550"
        raise NotImplementedError(msg)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a workbook into a structure."""
        msg = "apply is filled by US-1550"
        raise NotImplementedError(msg)


class EstimateExporter:
    """The exporter of the workbook of an estimate, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the estimate of a structure in a workbook."""
        msg = "export is filled by US-1550"
        raise NotImplementedError(msg)


def sheet_name(label: str) -> str:
    """Name a tab of a workbook from a label, as Excel admits it (#2190)."""
    msg = "sheet_name is filled by US-1550"
    raise NotImplementedError(msg)


ESTIMATE_FORMAT = EstimateFormat()
ESTIMATE_EXPORTER = EstimateExporter()
