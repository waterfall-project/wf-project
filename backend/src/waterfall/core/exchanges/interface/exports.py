# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports: the exporters a module registers, and the task that runs one.

An exporter gives the file of a kind of export, its type and its name, which the worker deposits
under ``exports/<task_id>.<ext>`` (EP-06, "Les exports"). The exchanges find the one of a kind
(``ExportKind``) in their registry, filled by the module that serves it at the import of its
interface — the planning for ``ms_project_schedule`` and ``task_tree_image`` (US-1430, US-1440),
EP-07 and EP-09 for theirs. The worker runs the task ``export`` through ``run_export``.

Declared by US-1380/L1; US-1430/L2 fills the exporter and the task.
"""

from typing import TYPE_CHECKING, Literal, Protocol

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task

# The kinds of an export, as the contract says them (``ExportKind``).
type ExportKind = Literal["ms_project_schedule", "estimate", "remaining", "task_tree_image"]


class Exporter(Protocol):
    """What gives the file of a kind of export, its type and its name: US-1430/L2 says how."""


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


def run_export(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Write the file of an export, in the transaction of its task (``export``)."""
    del session, task
    filled_by = "US-1430/L2"
    raise NotImplementedError(filled_by)
