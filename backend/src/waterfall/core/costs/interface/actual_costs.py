# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format ``actual_costs``: the extraction of the actual costs of the ERP (FLX-07; US-1610).

Registered at the import of the interface in the registry of the exchanges (``register_format``):
the format reads the header of an extraction against the mapping of the cost settings, analyses
its lines against those of the project — the WBS element, the document and its item, the date, the
amount, the columns kept — and applies its report, an entry of the log and the lines inserted or
updated on their document and item (EP-09, "Les coûts réels"). An import of the actual costs writes
in the project, under the permission to write its actual costs; it aims at no structure.

Declared by US-1580/L1 and registered without effect, as the socle of EP-07 registered the format
``estimate`` (#2370): the format refuses every head as a file it does not recognise (422
``FILE_FORMAT_UNREADABLE``, ``expected_format`` ``actual_costs``), as when no format served the
kind, so that an import of the actual costs never passes before US-1610/L1, which reads the header
and analyses, and US-1610/L2, which applies.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.exchanges.interface import LARGEST_FILE
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ImportScope, ImportTarget
    from waterfall.platform.audit import Act

FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
# The bytes of a file the header is read in: the whole file, at most what a deposit holds — a
# workbook is a zip, whose directory is at its end —, which US-1610/L1 reads.
HEADER_LENGTH = LARGEST_FILE


class ActualCostsFormat:
    """The format of an extraction of the actual costs, as the exchanges ask it (``Format``).

    It writes in the project, under the permission to write its actual costs.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "project"
    permission = "actual_costs.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse the head of a file that is not an extraction of actual costs: every one yet."""
        del session, head
        raise UnprocessableError(FILE_FORMAT_UNREADABLE, {"expected_format": "actual_costs"})

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of the actual costs on its mapping: none until US-1610/L1."""
        del session, target

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of an extraction against the lines of the project, writing nothing."""
        msg = "analyse is filled by US-1610/L1"
        raise NotImplementedError(msg)

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
