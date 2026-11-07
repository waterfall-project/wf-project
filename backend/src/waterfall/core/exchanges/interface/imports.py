# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps: the formats a module registers, the analysis and the application.

A format knows three things: read the header of a file deposited and say whether it recognises it,
analyse the file against the structure aimed at and give a report in codes without writing
anything, and apply a report in the transaction of the task, judging again what the analysis
accepted (EP-06, "L'import en deux temps"). The exchanges know no format: they find the one of a
kind (``ExchangeKind``) in their registry, filled by the module that serves it at the import of
its interface — the planning for ``ms_project_schedule`` (US-1430), EP-07 and EP-09 for theirs.

The worker runs the analysis and the application of an import (``import_analysis``,
``import_apply``) through ``run_analysis`` and ``run_apply``.

Declared by US-1380/L1; US-1420/L1 fills the format and the mechanics.
"""

from typing import TYPE_CHECKING, Literal, Protocol

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task

# The story that fills the analysis and the application.
FILLED_BY = "US-1420/L1"
# The kinds of an import, as the contract says them (``ExchangeKind``).
type ExchangeKind = Literal["ms_project_schedule", "estimate", "remaining", "actual_costs"]


class Format(Protocol):
    """What reads, analyses and applies a file of a kind of import: US-1420/L1 says how."""


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


def run_analysis(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Analyse the file of an import, in the transaction of its task (``import_analysis``)."""
    del session, task
    raise NotImplementedError(FILLED_BY)


def run_apply(session: Session, task: Task) -> Mapping[str, Any] | None:
    """Apply the report of an import, in the transaction of its task (``import_apply``)."""
    del session, task
    raise NotImplementedError(FILLED_BY)
