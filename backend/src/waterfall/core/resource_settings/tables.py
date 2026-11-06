# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the resource settings, private to the module (§4.4.1, regime "reference").

The tree of the organisation, the roles of resources under a node, a category and a calendar, the
calendars, one of them the default, and the units of duration, a single row. Nothing here is
deleted: an object is deactivated (``is_active``). That a node is never its own ancestor is the
service's rule, under its lock; that it is not its own parent, the database's. The codes and the
labels sort in the order of the code points (collation ``C``), and are bounded and never blank as
the contract bounds them.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The key of a table of one row.
SINGLE_ROW = 1
# The bounds the contract puts on a code and on a label.
CODE_LENGTH = 20
LABEL_LENGTH = 200
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# The unique index that keeps one calendar the default.
DEFAULT_INDEX = "uq_calendar_default"


class Audited(Base):
    """The columns of audit and the counter of the writes of a row that changes (WF-DAT-0070).

    An author is an account, or the platform when null: the bootstrap and the loader of the
    witness. Abstract: each table that has them declares them as its own.
    """

    __abstract__ = True

    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class OrgNode(Audited):
    """A node of the tree of the organisation (WF-REF-0070); a root has no parent."""

    __tablename__ = "org_node"
    __table_args__ = (
        *bounded("code", CODE_LENGTH),
        *bounded("label", LABEL_LENGTH),
        CheckConstraint("parent_id <> id", name="not_its_own_parent"),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("org_node.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool]


class Calendar(Audited):
    """A calendar: the hours worked on each day of the week (WF-REF-0110), one the default.

    The default is active (WF-REF-0120): a partial unique index keeps it single.
    """

    __tablename__ = "calendar"
    __table_args__ = (
        *bounded("label", LABEL_LENGTH),
        CheckConstraint(
            " AND ".join(f"{day} BETWEEN 0 AND 24" for day in DAYS), name="hours_of_a_day"
        ),
        CheckConstraint("is_active OR NOT is_default", name="default_active"),
        Index(DEFAULT_INDEX, "is_default", unique=True, postgresql_where=text("is_default")),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    monday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    tuesday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    wednesday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    thursday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    friday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    saturday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    sunday: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    is_default: Mapped[bool]
    is_active: Mapped[bool]


class ResourceRole(Audited):
    """A role of resources under a node, a category and a calendar, and its capacity.

    Its capacity is single, without a date (WF-REF-0090, WF-REF-0100): hours a month and a
    headcount, never negative.
    """

    __tablename__ = "resource_role"
    __table_args__ = (
        *bounded("code", CODE_LENGTH),
        *bounded("label", LABEL_LENGTH),
        CheckConstraint("monthly_hours >= 0", name="monthly_hours_not_negative"),
        CheckConstraint("headcount >= 0", name="headcount_not_negative"),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    org_node_id: Mapped[UUID] = mapped_column(
        ForeignKey(OrgNode.id, ondelete="RESTRICT"), index=True
    )
    # A category of the cost settings, named by its table: the key is the database's.
    cost_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_category.id", ondelete="RESTRICT"), index=True
    )
    calendar_id: Mapped[UUID] = mapped_column(
        ForeignKey(Calendar.id, ondelete="RESTRICT"), index=True
    )
    monthly_hours: Mapped[Decimal] = mapped_column(Numeric)
    headcount: Mapped[Decimal] = mapped_column(Numeric)
    is_active: Mapped[bool]


class DurationUnit(Audited):
    """The three constants the days, weeks and months of work convert by (WF-PLA-0160)."""

    __tablename__ = "duration_unit"
    __table_args__ = (
        CheckConstraint(f"id = {SINGLE_ROW}", name="single_row"),
        CheckConstraint(
            "hours_per_day > 0 AND hours_per_week > 0 AND days_per_month > 0",
            name="constants_positive",
        ),
        counted(),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    hours_per_day: Mapped[Decimal] = mapped_column(Numeric)
    hours_per_week: Mapped[Decimal] = mapped_column(Numeric)
    days_per_month: Mapped[Decimal] = mapped_column(Numeric)
