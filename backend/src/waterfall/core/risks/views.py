# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a risk is read as and written from, private to the module, offered by its interface.

The objects of ``interface/risks.py`` (US-2550/L1), moved here by US-2570/L1 so that the files that
read and write a risk build them without importing the interface, which imports those files: a
``RiskView`` is what a reading gives, which the register, the matrix and the portfolio read too;
a ``RiskEntry`` what a declaration sends, a ``RiskIdentityChange`` what a change of the identity
sends, a field not sent ``OMITTED``. Another module names them through the interface.
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
