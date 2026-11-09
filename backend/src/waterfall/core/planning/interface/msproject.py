# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The format and the exporter ``ms_project_schedule``: a planning of MS Project, MSPDI.

Registered at the import of the interface in the registries of the exchanges (``register_format``,
``register_exporter``): the format reads the header of a file, analyses it against a structure and
applies its report (US-1430/L3), the exporter writes the planning of a structure (US-1430/L4), both
through the reader and the writer of ``core/planning/msproject/`` (US-1430/L1) and the hardened
parser of the exchanges (EP-06, "Le format MS Project").

Declared by US-1380/L1; the exporter still raises ``NotImplementedError`` naming the story that
fills it (US-1430/L4), so that an export of a planning before it fails, and never passes without
effect.

The format is filled by US-1430/L3. The head of a file is recognised by its root, a ``Project`` of
the namespace of MS Project, after the declaration, the comments and the instructions; anything
else is refused (422 ``FILE_FORMAT_UNREADABLE``, ``expected_format``: MSPDI has no version). The
whole file is read by the reader at the analysis, which fails the import on a file it cannot read.
The analysis and the application build the same plan (``importing``), the application under the
lock of the structure, which the task of the exchanges takes after the revision and the project.
"""

from typing import TYPE_CHECKING, Any

# By their modules: their own imports reach this interface again, through the facets of a task.
from waterfall.core.planning import applying, importing
from waterfall.core.planning.msproject import UnreadableProjectError, read_project, recognised
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
    from waterfall.core.planning.msproject import ReadProject
    from waterfall.platform.audit import Act

# The bytes of the head of a file the header is read in: the declaration and the root of MSPDI.
HEADER_LENGTH = 4096
FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
KIND = "ms_project_schedule"


def _unreadable() -> UnprocessableError:
    """Give the refusal of a file that is no planning of MS Project."""
    return UnprocessableError(FILE_FORMAT_UNREADABLE, {"expected_format": KIND})


class MsProjectFormat:
    """The format of a planning of MS Project, as the exchanges ask it (``Format``).

    It writes a structure of the current revision, under the permission to write the planning.
    """

    header_length = HEADER_LENGTH
    scope: ImportScope = "structure"
    permission = "planning.write"

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse the head of a file that is not a planning of MS Project."""
        del session
        if not recognised(head):
            raise _unreadable()

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of a planning on the state of its structure: none."""
        del session, target

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a planning of MS Project against a structure, writing nothing."""
        read = _read(content)
        plan, items = importing.plan_import(session, target, read, lock=False)
        return importing.report_of(plan, read, items)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write the report of a planning of MS Project into a structure, judged again.

        The plan is built again under the lock of the structure: what changed since the analysis
        is judged as it now stands, and a refusal fails the import.
        """
        del report
        plan, _ = importing.plan_import(session, target, _read(content), lock=True)
        applying.apply_plan(session, plan, act)


def _read(content: bytes) -> ReadProject:
    """Read a whole file; one the reader cannot read is refused as its head would be."""
    try:
        return read_project(content)
    except UnreadableProjectError as error:
        raise _unreadable() from error


class MsProjectExporter:
    """The exporter of a planning in MSPDI, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Write the planning of a structure in MSPDI."""
        msg = "export is filled by US-1430/L4"
        raise NotImplementedError(msg)


MS_PROJECT_FORMAT = MsProjectFormat()
MS_PROJECT_EXPORTER = MsProjectExporter()
