# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a risk is read as and written from, private to the module, offered by its interface.

The objects of ``interface/risks.py`` (US-2550/L1), moved here by US-2570/L1 so that the files that
read and write a risk build them without importing the interface, which imports those files: a
``RiskView`` is what a reading gives, which the register, the matrix and the portfolio read too;
a ``RiskEntry`` what a declaration sends, a ``RiskIdentityChange`` what a change of the identity
sends, a field not sent ``OMITTED``. The objects of ``interface/register.py`` follow, moved here by
US-2600/L1 for the same reason: what the register asks for and gives; and those of
``interface/matrix.py``, moved by US-2600/L2: what the matrix gives. Another module names them
through the interface.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from waterfall.core.projects.interface import CommandAvailability

# The states of a risk, and its commands, as the contract says them (``RiskState``,
# ``RiskCommand``).
type RiskState = Literal["identified", "occurred", "dismissed"]
type RiskCommand = Literal["update", "update_provision", "review", "declare_occurrence", "delete"]


class Omitted(Enum):
    """A field not sent: the risk's stays (``RiskUpdate``, ``RiskProvisionUpdate``)."""

    FIELD = "omitted"


OMITTED = Omitted.FIELD


@dataclass(frozen=True, slots=True)
class ProvisionTask:
    """The task of the main structure bearing the provision line of a risk (``ProvisionTask``)."""

    node_id: UUID
    label: str


@dataclass(frozen=True, slots=True)
class RiskMatrixCell:
    """The cell of a risk: its levels on the bounds of the matrix, and its zone (WF-RIS-0040)."""

    probability_level: int
    severity_level: int
    zone: str


@dataclass(frozen=True, slots=True)
class RiskView:
    """A risk as a revision freezes it (``Risk``), with its commands for the reader.

    ``revision_id`` is the revision read; the labels of the category, of the subproject and of the
    task of its provision are resolved at the reading. ``commands`` are those the reader holds the
    permission of, in the order of ``RiskCommand``, none on a terminal project.
    """

    risk_id: UUID
    revision_id: UUID
    label: str
    description: str | None
    mitigation_notes: str | None
    probability: Decimal
    severity: Decimal
    provision_amount: Decimal
    occurrence_cost: Decimal | None
    occurred_reestimated_amount: Decimal | None
    state: RiskState
    structure_id: UUID
    provision_node_id: UUID | None
    provision_cost_category_id: UUID
    provision_cost_category_label: str
    provision_cost_category_is_active: bool
    provision_subproject_id: UUID | None
    provision_subproject_label: str | None
    provision_task: ProvisionTask | None
    matrix_cell: RiskMatrixCell
    last_review_on: date | None
    commands: tuple[CommandAvailability, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class RiskEntry:
    """A risk declared (``RiskWrite``): its identity, its probability, what bears its provision.

    A category, a subproject or a task not designated is ``None``: the only active category of the
    provision kind, no subproject, the first task of the first level (WF-RIS-0010, #786).
    """

    label: str
    probability: Decimal
    description: str | None = None
    mitigation_notes: str | None = None
    provision_cost_category_id: UUID | None = None
    provision_subproject_id: UUID | None = None
    provision_task_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RiskIdentityChange:
    """The identity of a risk written at the counter read (``RiskUpdate``).

    The label is always sent; a description or notes ``OMITTED`` stay the risk's, ``None`` empties
    them.
    """

    risk_id: UUID
    label: str
    lock_version: int
    description: str | Omitted | None = OMITTED
    mitigation_notes: str | Omitted | None = OMITTED


# The columns the register sorts on (``listRisks``, ``sort_by``).
type RiskColumn = Literal[
    "label",
    "probability",
    "severity",
    "provision_amount",
    "occurrence_cost",
    "occurred_reestimated_amount",
    "state",
    "last_review_on",
]


@dataclass(frozen=True, slots=True)
class Bounds[T]:
    """The two bounds of a column, each included, ``None`` when not given."""

    least: T | None = None
    most: T | None = None


@dataclass(frozen=True, slots=True)
class RiskFilters:
    """What the register keeps (``listRisks``): each column by its list, its search or its bounds.

    ``revision_id`` the revision read: the current one, or the last marked, when ``None``.
    """

    revision_id: UUID | None = None
    states: tuple[RiskState, ...] | None = None
    zones: tuple[str, ...] | None = None
    search: str | None = None
    probability: Bounds[Decimal] = Bounds()
    severity: Bounds[Decimal] = Bounds()
    provision_amount: Bounds[Decimal] = Bounds()
    occurrence_cost: Bounds[Decimal] = Bounds()
    occurred_reestimated_amount: Bounds[Decimal] = Bounds()
    last_review_on: Bounds[date] = Bounds()


@dataclass(frozen=True, slots=True)
class RiskSort:
    """How the register is sorted: by a column, or in the order of declaration when ``None``."""

    key: RiskColumn | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class RiskPage:
    """Which risks of the register are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ProvisionTotals:
    """The provision totals of the risks retained, by state, their sum, and the reserve."""

    identified: Decimal
    occurred: Decimal
    dismissed: Decimal
    total: Decimal
    reserve: Decimal


@dataclass(frozen=True, slots=True)
class RiskList:
    """A page of the register, how many risks the filters retain, and their totals."""

    risks: list[RiskView]
    total: int
    totals: ProvisionTotals


@dataclass(frozen=True, slots=True)
class MatrixLevel:
    """A level of an axis and its bounds (``RiskMatrixLevel``), the upper ``None`` at the last."""

    level: int
    lower: Decimal
    upper: Decimal | None


@dataclass(frozen=True, slots=True)
class MatrixCell:
    """A cell of the matrix, its zone, and how many identified risks it holds."""

    probability_level: int
    severity_level: int
    zone: str
    count: int


@dataclass(frozen=True, slots=True)
class MatrixPoint:
    """A risk the matrix places (``RiskMatrixPoint``), at the values of the risk read.

    ``severity_ratio`` its severity as a share of the base of the project, ``None`` on a base of
    nought, which relates it to nothing (#1240).
    """

    risk_id: UUID
    label: str
    probability: Decimal
    severity_amount: Decimal
    severity_ratio: Decimal | None
    provision_amount: Decimal
    state: RiskState
    zone: str


@dataclass(frozen=True, slots=True)
class RiskMatrix:
    """The matrix of a project in a revision (``RiskMatrix``): its levels, cells, points, totals."""

    probability_levels: tuple[MatrixLevel, ...]
    severity_levels: tuple[MatrixLevel, ...]
    cells: tuple[MatrixCell, ...]
    points: tuple[MatrixPoint, ...]
    totals: ProvisionTotals
