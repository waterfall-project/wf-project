# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``remaining``: the workbook of a remaining to commit (US-1630).

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a workbook « Reste à engager » (FLX-05),
analyses it by lineage against the lines of the main structure and applies its report through the
re-estimation; the exporter writes the remaining to commit of a revision (FLX-06) — XlsxWriter
writes, openpyxl reads, in ``remaining/excel/`` (EP-09, "Le format Excel du reste à engager").

Declared by US-1580/L1 and registered without effect, as the socle of EP-07 registered the format
``estimate`` (#2370): the format refuses every head as a file it does not recognise (422
``FILE_FORMAT_UNREADABLE``, ``expected_format`` ``remaining``), as when no format served the kind,
so that an import of a remaining to commit never passes before US-1630/L3; the methods it never
reaches and the export raise ``NotImplementedError`` naming the story that fills them.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.exchanges.interface import LARGEST_FILE
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
# The bytes of a file the header is read in: the whole file, at most what a deposit holds — a
# workbook is a zip, whose directory is at its end —, which US-1630 reads.
HEADER_LENGTH = LARGEST_FILE


class RemainingFormat:
    """The format of the workbook of a remaining to commit, as the exchanges ask it (``Format``).

    It writes the main structure of the current revision, under the permission to write the
    remaining to commit.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "structure"
    permission = "remaining.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse the head of a file that is not the workbook of a remaining: every one yet."""
        del session, head
        raise UnprocessableError(FILE_FORMAT_UNREADABLE, {"expected_format": "remaining"})

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of a remaining to commit on the state of its project: none yet."""
        del session, target

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a workbook against the main structure, writing nothing."""
        msg = "analyse is filled by US-1630/L3"
        raise NotImplementedError(msg)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a workbook into the main structure, through the re-estimation."""
        msg = "apply is filled by US-1630/L3"
        raise NotImplementedError(msg)


class RemainingExporter:
    """The exporter of the workbook of a remaining to commit, as the exchanges ask it."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the remaining to commit of a revision in a workbook."""
        msg = "export is filled by US-1630/L4"
        raise NotImplementedError(msg)


REMAINING_FORMAT = RemainingFormat()
REMAINING_EXPORTER = RemainingExporter()
