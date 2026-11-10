# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the estimate, private to the module (§4.4.1; EP-07, "Tables et migrations").

Regime "revised", partitioned by project as the nodes (WF-DAT-0050): the facet estimate line of a
node, and what a revision keeps of the reference — the rates it is priced at, and the images of the
roles, the calendars and the categories its lines employ at its marking (WF-REV-0090).

The facet names its node with its kind, and follows it (WF-DAT-0090): a line is deleted with its
node inside a current revision. Every other key refuses (``RESTRICT``); a rate and an image name
their revision alone, the objects of the reference they copy being free to change or to leave after
the marking. A marked revision deletes nothing: the triggers of the migration refuse any write of a
row of a marked revision, owner included, as they do for the tasks.

The amounts and the year of consumption of a line are kept, computed by the service in the
transaction of what changes them (EP-07, "Ce que le cadrage décide"); its budgeted amount is null
while the project has no reference. Its reference figures are null until the merge of an amendment
writes them (EP-08). What a review of the project writes on a line — its remaining to commit before
it, the mark of its re-estimation and the reason sent — is null until then (EP-09).
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The bound the contract puts on the label of a line; the years of a consumption (``Year``); the
# origins of a rate kept; the kinds of a nature of cost (``CostTypeKind``), which an image keeps.
LABEL_LENGTH = 300
YEARS = (2000, 2100)
RATE_ORIGINS = ("reference", "projected")
COST_TYPE_KINDS = ("labor", "non_labor", "provision")
# The clause of the partitioning of every revised table.
BY_PROJECT = "LIST (project_id)"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _not_negative(column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} >= 0", name=f"{column}_not_negative")


def _of_revision() -> ForeignKeyConstraint:
    """Name the revision of a row with its project, its partition; it refuses (migration 0025)."""
    return ForeignKeyConstraint(
        ["project_id", "revision_id"], ["revision.project_id", "revision.id"], ondelete="RESTRICT"
    )


class EstimateLine(Base):
    """The facet estimate line of a node: what it prices, and its amounts as last computed.

    A labour line names a role of resources and its hours, and no unit disbursement; any other
    line, a unit disbursement and neither role nor hours (WF-DEV-0020). Its subproject is one of its
    project's. Its columns of audit and its counter are its own, those of its node aside.
    """

    __tablename__ = "estimate_line"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "node_id", "kind"],
            ["node.project_id", "node.id", "node.kind"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("kind = 'estimate_line'", name="kind_estimate_line"),
        *bounded("label", LABEL_LENGTH),
        _not_negative("quantity"),
        _not_negative("hours"),
        _not_negative("unit_disbursement"),
        _not_negative("payment_delay_days"),
        # A labour line has its role and its hours, and no disbursement; any other the reverse.
        CheckConstraint("(resource_role_id IS NULL) = (hours IS NULL)", name="hours_of_a_role"),
        CheckConstraint(
            "(resource_role_id IS NULL) = (unit_disbursement IS NOT NULL)",
            name="unit_disbursement_without_role",
        ),
        CheckConstraint(
            f"consumption_year BETWEEN {YEARS[0]} AND {YEARS[1]}", name="consumption_year_bound"
        ),
        # The remaining to commit before the review (EP-09, migration 0027): the source line's
        # figures, copied as they were, which their own consistency holds.
        _not_negative("previous_quantity"),
        _not_negative("previous_hours"),
        _not_negative("previous_unit_disbursement"),
        _not_negative("previous_reestimated_amount"),
        # The questions of the reference: is a category, a role, a subproject employed? A partition
        # holds one project: its index needs the object alone.
        Index(None, "cost_category_id"),
        Index(None, "resource_role_id"),
        Index(None, "subproject_id"),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    node_id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    cost_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_category.id", ondelete="RESTRICT")
    )
    resource_role_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resource_role.id", ondelete="RESTRICT")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit_disbursement: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    payment_delay_days: Mapped[int] = mapped_column(Integer)
    subproject_id: Mapped[UUID | None]
    # Written by the merge of an amendment (EP-08), null until then.
    reference_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    reference_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference_unit_disbursement: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # Fixed by the lineage in the reference revision: null without one (WF-REV-0070).
    budgeted_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    reestimated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    consumption_year: Mapped[int] = mapped_column(SmallInteger)
    # The remaining to commit of the line in the last revision marked in the state In progress,
    # copied at the opening of the revision (EP-09); null before the first review, and for a line
    # created since.
    previous_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    previous_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    previous_unit_disbursement: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    previous_reestimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    # The mark of a re-estimation, its instant: written by ``setLineRemaining`` and the import of a
    # remaining to commit, never by the entry of the estimate nor by a copy; an amendment spares a
    # line that bears it (EP-08). The reason sent with it, kept and served by no reading.
    reestimated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    remaining_reason: Mapped[str | None] = mapped_column(Text)
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class RevisionRate(Base):
    """The hourly rate of a category a revision is priced at (WF-REV-0060): kept, or projected.

    One per category of a revision; written while the revision is current, never after.
    """

    __tablename__ = "revision_rate"
    __table_args__ = (
        _of_revision(),
        CheckConstraint(_in("origin", RATE_ORIGINS), name="origin_known"),
        CheckConstraint("amount >= 0.01", name="amount_positive"),
        UniqueConstraint("revision_id", "cost_category_id", "project_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    cost_category_id: Mapped[UUID]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    origin: Mapped[str] = mapped_column(Text)


class Image(Base):
    """What an image of an object of the reference keeps: its audit and its counter at the marking.

    Abstract: each image declares them as its own. Its texts are those of the object, bounded where
    it lives; its authors are copied, not keys: an image outlives what it names.
    """

    __abstract__ = True

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None]
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None]
    lock_version: Mapped[int] = mapped_column(Integer)


class RevisionRole(Image):
    """A role of resources as a revision marked keeps it (``ResourceRoleImage``)."""

    __tablename__ = "revision_role"
    __table_args__ = (
        _of_revision(),
        UniqueConstraint("revision_id", "resource_role_id", "project_id"),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    resource_role_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    org_node_id: Mapped[UUID]
    org_node_label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    cost_category_id: Mapped[UUID]
    cost_category_label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    calendar_id: Mapped[UUID]
    calendar_label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    monthly_hours: Mapped[Decimal] = mapped_column(Numeric)
    headcount: Mapped[Decimal] = mapped_column(Numeric)


class RevisionCalendar(Image):
    """A calendar as a revision marked keeps it, its hours of each day (``CalendarImage``)."""

    __tablename__ = "revision_calendar"
    __table_args__ = (
        _of_revision(),
        UniqueConstraint("revision_id", "calendar_id", "project_id"),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    calendar_id: Mapped[UUID]
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    monday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    tuesday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    wednesday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    thursday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    friday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    saturday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    sunday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    is_default: Mapped[bool] = mapped_column(Boolean)


class RevisionCategory(Image):
    """A category of cost as a revision marked keeps it, with its nature (``CostCategoryImage``)."""

    __tablename__ = "revision_category"
    __table_args__ = (
        _of_revision(),
        CheckConstraint(_in("cost_type_kind", COST_TYPE_KINDS), name="cost_type_kind_known"),
        UniqueConstraint("revision_id", "cost_category_id", "project_id"),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    cost_category_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    cost_type_id: Mapped[UUID]
    cost_type_label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    cost_type_kind: Mapped[str] = mapped_column(Text)
    cost_type_is_active: Mapped[bool] = mapped_column(Boolean)
    accounting_code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
