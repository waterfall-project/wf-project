# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the workbook of an estimate is written from, in memory (US-1550/L1).

The exporter of the format (US-1550/L4) reads the estimate of a structure and fills this model;
the writer turns it into a workbook without a database, without the exchanges and without a clock
(the instant of the export is given). A lot, a tab, a task and a line are values, as the
workbook shows them: the amounts are the ones the service computed, never recomputed here.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

# What a nature of cost is: the labour is priced by an hourly rate, the others by a disbursement,
# a provision (for a risk) is one of them that the workbook does not let the user choose.
NatureKind = Literal["labour", "disbursement", "provision"]


@dataclass(frozen=True)
class Nature:
    """A nature of cost, which the breakdown of the workbook sums."""

    name: str
    kind: NatureKind


@dataclass(frozen=True)
class Category:
    """A category of cost: its code, its label, its nature and, for labour, its rate.

    ``code`` is the code that designates the category in the workbook: its accounting code
    (``CostCategory.accounting_code``, WF-REF-0040, #2688), never its technical code. It is the
    one the entry « label (code) », the column « Code comptable » and the hours by accounting code
    write, the one a role and a line name their category by, and the one the import reads back.
    """

    code: str
    label: str
    nature: str
    hourly_rate: Decimal | None = None


@dataclass(frozen=True)
class Role:
    """A role of resource, with its department (a path) and the category of labour it costs by.

    ``category`` is the ``code`` of that category: its accounting code.
    """

    code: str
    label: str
    department: str
    category: str


@dataclass(frozen=True)
class Subproject:
    """A subproject a line may be placed under."""

    code: str
    label: str


@dataclass(frozen=True)
class Line:
    """A line of the estimate, under a task.

    Exactly one of ``role`` and ``category`` is given (their codes, the accounting code for a
    category); a line of labour has hours, a line of disbursement has a disbursement. ``amount``
    is the amount of the line, inflation included, that the service computed: empty for a line the
    service has not priced.
    """

    lineage: str
    role: str | None
    category: str | None
    label: str
    quantity: Decimal
    hours: Decimal | None = None
    disbursement: Decimal | None = None
    payment_delay: int | None = None
    subproject: str | None = None
    amount: Decimal | None = None


@dataclass(frozen=True)
class Task:
    """A task of the structure, with its lines (possibly none: a summary task, a lot)."""

    lineage: str
    number: str
    label: str
    start: date
    end: date
    description: str
    lines: tuple[Line, ...] = ()


@dataclass(frozen=True)
class Tab:
    """A tab of lines: a package, a lot outside its packages, or the tasks outside any lot.

    ``number`` and ``task_label`` give the name of the tab (« 1.1 Label »); ``label`` is what the
    summary shows.
    """

    number: str
    task_label: str
    label: str
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class Lot:
    """A lot of the structure, with the tabs of its packages and of its own tasks."""

    number: str
    label: str
    tabs: tuple[Tab, ...]


@dataclass(frozen=True)
class Estimate:
    """The estimate of a structure of a revision, as the workbook says it.

    The writer trusts the model to be coherent: a line names a role or a category of the
    reference, a category a nature of it. The exporter (US-1550/L4) builds it from the service, so
    it keeps that coherence; the writer raises a bare ``KeyError`` on a model that does not.
    """

    company: str
    client: str
    project: str
    revision: str
    structure: str
    reference_year: int
    currency: str
    exported_at: datetime
    natures: tuple[Nature, ...]
    categories: tuple[Category, ...]
    roles: tuple[Role, ...]
    subprojects: tuple[Subproject, ...]
    lots: tuple[Lot, ...]
    outside_lot: Tab | None = None
