# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the workbook « Reste à engager » is written from, in memory (US-1630/L1).

The exporter of the format (US-1630/L4) reads a revision and fills this model; the writer turns it
into a workbook without a database, without the exchanges and without a clock. The amounts of the
headers of a tab are the ones the services computed for the revision exported
(``remaining_indicators`` and ``costs``): the workbook shows them and never recomputes them.
The reference (natures, categories, roles) is the one of the workbook « Devis », and so are its
types.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from waterfall.core.estimate.excel.model import Category, Nature, Role

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

__all__ = [
    "Category",
    "Nature",
    "RemainingLine",
    "RemainingTab",
    "RemainingTask",
    "RemainingWorkbook",
    "Role",
    "TaskState",
    "remaining_days",
]

# A task finished is not in the file: only these two states are written.
TaskState = Literal["started", "not_started"]


def remaining_days(quantity: Decimal, hours: Decimal, hours_per_day: Decimal) -> Decimal:
    """Give the days left of a line of labour: quantity times effort over hours per day.

    The one definition of the column « Jours restants »: the import (US-1630/L3) recomputes it to
    tell a cell the user changed from one the export wrote.
    """
    return quantity * hours / hours_per_day


@dataclass(frozen=True)
class RemainingLine:
    """A line of a task not finished, as the review shows it.

    Exactly one of ``role`` and ``category`` is given (their codes). ``quantity`` and ``hours``
    (the effort of one unit) give the days left of a line of labour; ``reestimated_amount`` is the
    amount left of a line of disbursement, inflation included. ``previous`` is the amount
    reestimated at the previous review, empty when the line has none.
    """

    lineage: str
    role: str | None
    category: str | None
    label: str
    budget: Decimal
    previous: Decimal | None
    quantity: Decimal
    hours: Decimal
    reestimated_amount: Decimal


@dataclass(frozen=True)
class RemainingTask:
    """A task not finished, with its lines, its state and the inflation of its year."""

    lineage: str
    number: str
    label: str
    state: TaskState
    inflation: Decimal
    description: str
    lines: tuple[RemainingLine, ...] = ()


@dataclass(frozen=True)
class RemainingTab:
    """A tab: a subproject, or the lines outside any (``code`` empty).

    ``budget`` is the amount budgeted of all its lines, the tasks finished included;
    ``actual_costs`` the costs charged to it; ``provisions`` the remaining of the provision lines
    of the risks identified (EP-08, zero until then).
    """

    code: str
    label: str
    budget: Decimal
    actual_costs: Decimal
    provisions: Decimal
    tasks: tuple[RemainingTask, ...]


@dataclass(frozen=True)
class RemainingWorkbook:
    """The remaining to commit of a revision, as the workbook says it."""

    company: str
    client: str
    project: str
    revision: str
    structure: str
    review_date: date
    currency: str
    exported_at: datetime
    hours_per_day: Decimal
    natures: tuple[Nature, ...]
    categories: tuple[Category, ...]
    roles: tuple[Role, ...]
    subprojects: tuple[RemainingTab, ...]
    outside: RemainingTab | None = None
