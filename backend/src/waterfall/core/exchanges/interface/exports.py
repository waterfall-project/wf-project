# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports: the exporters a module registers, the task that runs one, and its result.

An exporter gives the file of a kind of export, its type and its name, which the worker deposits
under ``exports/<task_id>.<ext>`` (EP-06, "Les exports"). The exchanges find the one of a kind
(``ExportKind``) in their registry, filled by the module that serves it at the import of its
interface — the planning for ``ms_project_schedule`` and ``task_tree_image`` (US-1430, US-1440),
EP-07 and EP-09 for theirs. ``request_export`` deposits the task (``requestExport``), the worker
runs it through ``run_export``, and ``result_of`` and ``consumed`` serve its file once
(``getBackgroundTaskResult``).

Declared by US-1380/L1; US-1430/L2 fills the mechanics, and gives each its arguments and its
result where the design leaves them open.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.platform.tasks import Task

# The kinds of an export, as the contract says them (``ExportKind``).
type ExportKind = Literal["ms_project_schedule", "estimate", "remaining", "task_tree_image"]


@dataclass(frozen=True, slots=True)
class ExportOrder:
    """What an export is asked of: the revision, its structure, and the account that asks.

    ``depth`` is the level an image of the task tree keeps (null, the whole depth), and the account
    names the language of a header; ``review_date`` is the one of a remaining to commit (EP-09).
    """

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    requested_by: UUID
    depth: int | None
    review_date: date | None


@dataclass(frozen=True, slots=True)
class ExportedFile:
    """The file of an export: its content, its type and the name it is downloaded under."""

    content: bytes
    media_type: str
    filename: str


class Exporter(Protocol):
    """What gives the file of a kind of export, in the transaction of the task ``export``."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Give the file of an export, writing nothing."""
        ...


# The exporter of each kind of export, in the order of their registration.
_EXPORTERS: Registry[tuple[ExportKind, Exporter]] = Registry("exchanges.exporters")


def register_exporter(kind: ExportKind, exporter: Exporter) -> Callable[[], None]:
    """Add the exporter of a kind of export; give its withdrawal; refused if the kind has one."""
    if kind in exporters():
        msg = f"the kind {kind} has an exporter already"
        raise ValueError(msg)
    return _EXPORTERS.register((kind, exporter))


def exporters() -> Mapping[ExportKind, Exporter]:
    """Give the exporter of each kind of export registered, by kind."""
    return dict(_EXPORTERS.entries())


def request_export(session: Session, project_id: UUID, kind: ExportKind, act: Act) -> None:
    """Deposit the task of an export, under the command ``export_*`` of its revision (202)."""
    msg = "request_export is filled by US-1430/L2"
    raise NotImplementedError(msg)


def run_export(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Write the file of an export, in the transaction of its task (``export``)."""
    msg = "run_export is filled by US-1430/L2"
    raise NotImplementedError(msg)


def result_of(session: Session, task_id: UUID, requested_by: UUID) -> None:
    """Give where the file of an export that succeeded lies, unless it was consumed."""
    msg = "result_of is filled by US-1430/L2"
    raise NotImplementedError(msg)


def consumed(session: Session, task_id: UUID) -> None:
    """Mark the result of an export consumed, once its last byte is sent."""
    msg = "consumed is filled by US-1430/L2"
    raise NotImplementedError(msg)
