# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the risks, private to the module (§4.4.1; EP-08, "Tables et migrations").

Regime "project": the identity of a risk (``risk``), not revised — its label, its description, its
mitigation notes, its counter and its audit (H-02). Its counter (``Risk.lock_version``) advances at
every write of the risk, of its evaluation or of its own estimate, and never goes back, abandonment
and undoing included.

Regime "revised", partitioned by project as the cost structures (WF-DAT-0050), each row naming its
revision with its project:

- ``risk_evaluation``, one row by risk and by revision that bears it: its probability, its state,
  its own structure, its provision line (null out of the state identified), the category, the
  subproject and the lineage of the task its provision designates — kept when it is dismissed, for
  its return —, its cost at occurrence (null out of the state occurred). The copy of a revision
  takes it up, the abandonment deletes it with the revision;
- ``risk_review``, one row by review, of the revision it was made in, never copied: its day, the
  probability, the severity and the state it retained;
- ``risk_reference_share``, one row by risk and by reference revision: the provision the risk bears
  in that reference, written when the revision becomes the reference, deleted when a designation is
  corrected. The reserve is their sum (M-01).

Every key refuses (``RESTRICT``). The triggers of the migration ``0035`` refuse any write of an
evaluation or of a review of a marked revision, owner included; a share is written once its revision
is marked — the reference is a marked revision — and is under no such guard.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The states of a risk (``RiskState``); the bound the contract puts on its label.
STATES = ("identified", "occurred", "dismissed")
LABEL_LENGTH = 300
# The precision of a probability (``Percent``, a ratio from 0 to 1, as the probability of winning of
# a project) and of an amount (``Money``).
PROBABILITY_PRECISION, PROBABILITY_SCALE = 5, 4
AMOUNT_PRECISION, AMOUNT_SCALE = 14, 2
# The clause of the partitioning of every revised table.
BY_PROJECT = "LIST (project_id)"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _of_revision() -> ForeignKeyConstraint:
    """Name the revision of a row with its project, its partition; it refuses."""
    return ForeignKeyConstraint(
        ["project_id", "revision_id"], ["revision.project_id", "revision.id"], ondelete="RESTRICT"
    )


def _of_risk() -> ForeignKeyConstraint:
    """Name the risk of a row with its project, so that no row binds two projects; it refuses."""
    return ForeignKeyConstraint(
        ["project_id", "risk_id"], ["risk.project_id", "risk.id"], ondelete="RESTRICT"
    )


def _probability() -> CheckConstraint:
    return CheckConstraint("probability BETWEEN 0 AND 1", name="probability_ratio")


class Created(Base):
    """The columns of the creation of a row (WF-DAT-0070), its author an account, or the platform.

    Abstract: each table that has them declares them as its own.
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class Stamped(Created):
    """The columns of audit of a row that changes (WF-DAT-0070): its creation, its last change."""

    __abstract__ = True

    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class Risk(Stamped):
    """The identity of a risk, a datum of its project (H-02), and its counter.

    What a key of a revised row names is the risk with its project (``uq_risk_project_id``).
    """

    __tablename__ = "risk"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        *bounded("label", LABEL_LENGTH),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    # Null when none is entered.
    description: Mapped[str | None] = mapped_column(Text)
    mitigation_notes: Mapped[str | None] = mapped_column(Text)
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")


class RiskEvaluation(Stamped):
    """The evaluation of a risk in a revision: what the revision freezes of it (WF-RIS-0030).

    Its own structure is of its revision and of its risk (``structure_id``, a structure of kind
    risk); its provision line is a node of its revision, there while it is identified alone
    (WF-RIS-0010); its cost at occurrence there while
    it is occurred alone (WF-RIS-0060). The category of its provision is always there; its
    subproject and the lineage of the task that bears its line, null without a designation.
    """

    __tablename__ = "risk_evaluation"
    __table_args__ = (
        # The structure with its revision and its risk: an own estimate of the revision of the
        # evaluation, of this risk — a risk names a structure of kind risk alone. The structure
        # names its risk in turn, which refuses: no key of the evaluation to the risk repeats it.
        ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id", "risk_id"],
            [
                "cost_structure.project_id",
                "cost_structure.id",
                "cost_structure.revision_id",
                "cost_structure.risk_id",
            ],
            ondelete="RESTRICT",
        ),
        # The provision line with its revision: a node of the revision of the evaluation.
        ForeignKeyConstraint(
            ["project_id", "provision_node_id", "revision_id"],
            ["node.project_id", "node.id", "node.revision_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "provision_subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        _probability(),
        CheckConstraint(_in("state", STATES), name="state_known"),
        CheckConstraint(
            "(provision_node_id IS NOT NULL) = (state = 'identified')",
            name="provision_when_identified",
        ),
        CheckConstraint(
            "(occurrence_cost IS NOT NULL) = (state = 'occurred')", name="cost_when_occurred"
        ),
        CheckConstraint("occurrence_cost >= 0", name="occurrence_cost_not_negative"),
        # The own estimate of one risk, and the provision line of one risk, in a revision.
        UniqueConstraint("structure_id", "project_id"),
        UniqueConstraint("provision_node_id", "project_id"),
        # The questions of the reference: is a category or a subproject employed? A partition holds
        # one project: its index needs the object alone.
        Index(None, "provision_cost_category_id"),
        Index(None, "provision_subproject_id"),
        Index(None, "risk_id"),
        # The evaluations of a revision — the register, the matrix, the reserve, the copy read
        # them so —, which the key, the risk first, does not serve.
        Index(None, "revision_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    probability: Mapped[Decimal] = mapped_column(Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE))
    state: Mapped[str] = mapped_column(Text)
    structure_id: Mapped[UUID]
    provision_node_id: Mapped[UUID | None]
    provision_cost_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_category.id", ondelete="RESTRICT")
    )
    provision_subproject_id: Mapped[UUID | None]
    # The lineage of the task the risk designates for its line (WF-DAT-0030): none, the first task
    # of the first level bears it (#786).
    provision_task_lineage_id: Mapped[UUID | None]
    occurrence_cost: Mapped[Decimal | None] = mapped_column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE))


class RiskReview(Created):
    """A review of a risk, dated, of the revision it was made in (WF-RIS-0010, WF-RIS-0040).

    Never changed: deleted with its revision, or by the undoing of the entry that wrote it. Its
    author is its actor (``RiskReview.actor``).
    """

    __tablename__ = "risk_review"
    __table_args__ = (
        _of_revision(),
        _of_risk(),
        _probability(),
        CheckConstraint("severity >= 0", name="severity_not_negative"),
        CheckConstraint(_in("state", STATES), name="state_known"),
        Index(None, "risk_id"),
        Index(None, "revision_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    reviewed_on: Mapped[date] = mapped_column(Date)
    probability: Mapped[Decimal] = mapped_column(Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE))
    severity: Mapped[Decimal] = mapped_column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE))
    state: Mapped[str] = mapped_column(Text)


class RiskReferenceShare(Created):
    """The provision a risk bears in a reference revision of its project (WF-RIS-0050, M-01).

    For a risk the reference bears identified, the amount of its provision line; for one occurred
    or dismissed before it, the share it had in the reference before.
    """

    __tablename__ = "risk_reference_share"
    __table_args__ = (
        _of_revision(),
        _of_risk(),
        CheckConstraint("provision_amount >= 0", name="provision_amount_not_negative"),
        Index(None, "risk_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID] = mapped_column(primary_key=True)
    provision_amount: Mapped[Decimal] = mapped_column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE))
