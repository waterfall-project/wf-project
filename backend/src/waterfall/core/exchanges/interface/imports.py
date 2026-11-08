# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps: the formats a module registers, the deposit, the analysis, the apply.

A format knows three things: read the header of a file deposited and say whether it recognises it,
analyse the file against the structure aimed at and give a report in codes without writing
anything, and apply a report in the transaction of the task, judging again what the analysis
accepted (EP-06, "L'import en deux temps"). The exchanges know no format: they find the one of a
kind (``ExchangeKind``) in their registry, filled by the module that serves it at the import of
its interface — the planning for ``ms_project_schedule`` (US-1430), EP-07 and EP-09 for theirs —,
and read of the file only the header the format asks for (``Format.header_length``).

The deposit of a file (``uploadFile``: ``deposit``), the opening of an import (``open_import``:
the header by the format, the conditions, the task of the analysis), its reading and its list
(``read_import``, ``list_imports``), its abandonment (``abandon_import``) and its application
(``apply_import``: the conditions judged again, the task) serve the API; the worker runs the
analysis and the application (``import_analysis``, ``import_apply``) through ``run_analysis`` and
``run_apply``.

Declared by US-1380/L1; US-1420/L1 fills the mechanics, and gives each its arguments and its
result where the design leaves them open.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.platform.tasks import Task

# The kinds of an import, as the contract says them (``ExchangeKind``).
type ExchangeKind = Literal["ms_project_schedule", "estimate", "remaining", "actual_costs"]


@dataclass(frozen=True, slots=True)
class ImportTarget:
    """The structure an import aims at, and its revision.

    The revision is the current one, or the last marked one, whose copy the application creates.
    """

    project_id: UUID
    revision_id: UUID
    structure_id: UUID


class Format(Protocol):
    """What reads, analyses and applies a file of a kind of import.

    ``header_length`` is the number of bytes of the head of the file ``read_header`` receives.
    ``read_header`` refuses a head it does not recognise, by a typed exception
    (``FILE_FORMAT_UNREADABLE``, ``expected_format``, ``expected_version``). ``analyse`` gives the
    report of the file against the structure aimed at, in codes and parameters (``ImportReport`` as
    the contract reads it), writing nothing. ``apply`` writes the report into the structure, in the
    transaction of the task and under its lock, judging again what the analysis accepted.
    """

    header_length: int

    def read_header(self, head: bytes) -> None:
        """Refuse the head of a file this format does not recognise."""
        ...

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a file against the structure aimed at, writing nothing."""
        ...

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        content: bytes,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write a report into the structure, judging again what the analysis accepted."""
        ...


# The format of each kind of import, in the order of their registration.
_FORMATS: Registry[tuple[ExchangeKind, Format]] = Registry("exchanges.formats")


def register_format(kind: ExchangeKind, form: Format) -> Callable[[], None]:
    """Add the format of a kind of import; give its withdrawal; refused if the kind has one."""
    if kind in formats():
        msg = f"the kind {kind} has a format already"
        raise ValueError(msg)
    return _FORMATS.register((kind, form))


def formats() -> Mapping[ExchangeKind, Format]:
    """Give the format of each kind of import registered, by kind."""
    return dict(_FORMATS.entries())


def deposit(session: Session, upload_id: UUID, content: bytes, act: Act) -> None:
    """Keep a file deposited for an import, in one piece, for twenty-four hours (``uploadFile``)."""
    msg = "deposit is filled by US-1420/L1"
    raise NotImplementedError(msg)


def open_import(session: Session, project_id: UUID, upload_id: UUID, act: Act) -> None:
    """Open an import of a file deposited, and deposit the task of its analysis (``openImport``)."""
    msg = "open_import is filled by US-1420/L1"
    raise NotImplementedError(msg)


def read_import(session: Session, project_id: UUID, import_id: UUID) -> None:
    """Read an import of a project, its expiry judged at the reading (``getImport``)."""
    msg = "read_import is filled by US-1420/L1"
    raise NotImplementedError(msg)


def list_imports(session: Session, project_id: UUID) -> None:
    """List the imports of a project (``listImports``)."""
    msg = "list_imports is filled by US-1420/L1"
    raise NotImplementedError(msg)


def abandon_import(session: Session, project_id: UUID, import_id: UUID, act: Act) -> None:
    """Abandon an import awaiting its decision, its file deleted (``abandonImport``)."""
    msg = "abandon_import is filled by US-1420/L1"
    raise NotImplementedError(msg)


def apply_import(session: Session, project_id: UUID, import_id: UUID, act: Act) -> None:
    """Judge an import again and deposit the task of its application (``applyImport``)."""
    msg = "apply_import is filled by US-1420/L1"
    raise NotImplementedError(msg)


def run_analysis(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Analyse the file of an import, in the transaction of its task (``import_analysis``)."""
    msg = "run_analysis is filled by US-1420/L1"
    raise NotImplementedError(msg)


def run_apply(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Apply the report of an import, in the transaction of its task (``import_apply``)."""
    msg = "run_apply is filled by US-1420/L1"
    raise NotImplementedError(msg)
