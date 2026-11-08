# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``ms_project_schedule``: a planning of MS Project, MSPDI.

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a file, analyses it against a structure and
applies its report (US-1430/L3), the exporter writes the planning of a structure (US-1430/L4), both
through the reader and the writer of ``core/planning/msproject/`` (US-1430/L1) and the hardened
parser of the exchanges (EP-06, "Le format MS Project").

Declared by US-1380/L1; each method raises ``NotImplementedError`` naming the story that fills it,
so that an import or an export of a planning before it fails, and never passes without effect.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ExportedFile, ExportOrder, ImportTarget
    from waterfall.platform.audit import Act

# The bytes of the head of a file the header is read in: the declaration and the root of MSPDI.
HEADER_LENGTH = 4096


class MsProjectFormat:
    """The format of a planning of MS Project, as the exchanges ask it (``Format``)."""

    header_length = HEADER_LENGTH

    def read_header(self, head: bytes) -> None:
        """Refuse the head of a file that is not a planning of MS Project."""
        msg = "read_header is filled by US-1430/L3"
        raise NotImplementedError(msg)

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a planning of MS Project against a structure, writing nothing."""
        msg = "analyse is filled by US-1430/L3"
        raise NotImplementedError(msg)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a planning of MS Project into a structure."""
        msg = "apply is filled by US-1430/L3"
        raise NotImplementedError(msg)


class MsProjectExporter:
    """The exporter of a planning in MSPDI, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the planning of a structure in MSPDI."""
        msg = "export is filled by US-1430/L4"
        raise NotImplementedError(msg)


MS_PROJECT_FORMAT = MsProjectFormat()
MS_PROJECT_EXPORTER = MsProjectExporter()
