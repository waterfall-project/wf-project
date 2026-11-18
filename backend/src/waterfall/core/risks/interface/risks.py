# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared, read and renamed (``createRisk``, ``getRisk``, ``updateRisk``; US-2570).

A risk is declared with its own estimate, a structure of the current revision of the kind ``risk``,
and its provision line in the main structure, under the task, the category and the subproject the
declaration designates or the defaults (WF-RIS-0010, #786): the current revision created first when
the project has none. It is read in a revision, which freezes the version of its own estimate, of
its probability and of its state (WF-RIS-0030): its severity is the total of its own estimate, its
provision that severity weighted by its probability while it is identified, and the share it held
in the reference revision once occurred or dismissed (WF-RIS-0040, WF-RIS-0050). Its identity — its
label, its description, its notes — is a datum of the project (H-02), written at the counter of the
risk read, which advances at every write of the risk, of its evaluation or of its own estimate.

What a reading gives is a ``RiskView``, which the register, the matrix and the portfolio read too;
the rules of its computed fields (``Risk.computed_fields``) follow from its state alone, and the API
writes them.

Declared by US-2550/L1, the socle of EP-08; filled by US-2570/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import CommandAvailability, Viewer

# The states of a risk, and its commands, as the contract says them (``RiskState``,
# ``RiskCommand``).
type RiskState = Literal["identified", "occurred", "dismissed"]
type RiskCommand = Literal["update", "update_provision", "review", "declare_occurrence", "delete"]


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
    """The identity of a risk written at the counter read (``RiskUpdate``)."""

    risk_id: UUID
    label: str
    description: str | None
    mitigation_notes: str | None
    lock_version: int


def create_risk(
    session: Session, project_id: UUID, entry: RiskEntry, writer: Writer, viewer: Viewer
) -> RiskView:
    """Declare a risk in the current revision, its own estimate and its provision line with it."""
    msg = "create_risk is filled by US-2570/L1"
    raise NotImplementedError(msg)


def read_risk(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> RiskView:
    """Read a risk in a revision: the current one, or the last marked, when none is named."""
    msg = "read_risk is filled by US-2570/L1"
    raise NotImplementedError(msg)


def update_risk(
    session: Session, project_id: UUID, change: RiskIdentityChange, writer: Writer, viewer: Viewer
) -> RiskView:
    """Write the identity of a risk at the counter read, and read it in the current revision."""
    msg = "update_risk is filled by US-2570/L1"
    raise NotImplementedError(msg)
