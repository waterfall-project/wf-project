# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the cost settings, private to the module (§4.4.1, regime "reference").

The natures and the categories of cost, the hourly rates of a category by year, the settings the
installation shares — its single row read whole and written field by field, under the permission
of each, by this module and, for the matrix and the thresholds, by the two modules that hold their
rules (``risk_settings``, ``indicator_settings``) — and the mapping of the extraction of the actual
costs, a single row and its labels. Nothing here is deleted but a label of the mapping, which its
whole writing replaces: an object of the reference is deactivated (``is_active``). The codes and
the labels sort in the order of the code points (collation ``C``), and are bounded and never blank
as the contract bounds them.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The key of a table of one row.
SINGLE_ROW = 1
# The kinds of a nature of cost, the zones of the matrix of risks and the columns the import of
# the actual costs reads, as the contract says them (`CostTypeKind`, `AlertZone`,
# `ActualCostSourceColumn`).
KINDS = ("labor", "non_labor", "provision")
ZONES = ("nominal", "watch", "alert")
SOURCE_COLUMNS = ("wbs_element", "document_number", "document_item", "document_date", "amount")
LABEL_KINDS = ("read", "kept")
# The bounds the contract puts on a code and on a label, and on the year of a rate (`Year`).
CODE_LENGTH = 20
LABEL_LENGTH = 200
YEARS = (2000, 2100)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


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


class ReferenceSetting(Audited):
    """The settings the installation shares: its currency and name, the matrix, the thresholds.

    The bounds and the thresholds are fractions, as the contract writes them (``0.25``); the
    sixteen zones of the matrix are ranked by level of probability, then of severity.
    """

    __tablename__ = "reference_setting"
    __table_args__ = (
        CheckConstraint(f"id = {SINGLE_ROW}", name="single_row"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_form"),
        *bounded("company_name", LABEL_LENGTH),
        CheckConstraint(
            "probability_bound_1 < probability_bound_2 "
            "AND probability_bound_2 < probability_bound_3",
            name="probability_bounds_increasing",
        ),
        CheckConstraint(
            "severity_bound_1 < severity_bound_2 AND severity_bound_2 < severity_bound_3",
            name="severity_bounds_increasing",
        ),
        CheckConstraint(
            "array_ndims(risk_zones) = 1 AND cardinality(risk_zones) = 16",
            name="risk_zones_sixteen",
        ),
        CheckConstraint(
            f"risk_zones <@ ARRAY[{', '.join(repr(zone) for zone in ZONES)}]",
            name="risk_zones_known",
        ),
        CheckConstraint(
            " AND ".join(
                f"{threshold} > 0 AND {threshold} < 1"
                for threshold in ("cost_watch", "cost_alert", "schedule_watch", "schedule_alert")
            ),
            name="thresholds_between_zero_and_one",
        ),
        CheckConstraint(
            "cost_alert < cost_watch AND schedule_alert < schedule_watch",
            name="alert_below_watch",
        ),
        CheckConstraint(
            "max_weeks_between_reviews BETWEEN 1 AND 104", name="max_weeks_between_reviews_bound"
        ),
        counted(),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    # Chosen at the bootstrap, never written afterwards (WF-REF-0140).
    currency_code: Mapped[str] = mapped_column(Text)
    company_name: Mapped[str] = mapped_column(Text)
    probability_bound_1: Mapped[Decimal] = mapped_column(Numeric)
    probability_bound_2: Mapped[Decimal] = mapped_column(Numeric)
    probability_bound_3: Mapped[Decimal] = mapped_column(Numeric)
    severity_bound_1: Mapped[Decimal] = mapped_column(Numeric)
    severity_bound_2: Mapped[Decimal] = mapped_column(Numeric)
    severity_bound_3: Mapped[Decimal] = mapped_column(Numeric)
    risk_zones: Mapped[list[str]] = mapped_column(ARRAY(Text))
    cost_watch: Mapped[Decimal] = mapped_column(Numeric)
    cost_alert: Mapped[Decimal] = mapped_column(Numeric)
    schedule_watch: Mapped[Decimal] = mapped_column(Numeric)
    schedule_alert: Mapped[Decimal] = mapped_column(Numeric)
    max_weeks_between_reviews: Mapped[int] = mapped_column(SmallInteger)


class CostType(Audited):
    """A nature of cost, of one of three kinds (WF-REF-0030); its code unique, deactivated too."""

    __tablename__ = "cost_type"
    __table_args__ = (
        *bounded("code", CODE_LENGTH),
        *bounded("label", LABEL_LENGTH),
        CheckConstraint(_in("kind", KINDS), name="kind_known"),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    kind: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool]


class CostCategory(Audited):
    """A category of cost under its nature (WF-REF-0040); its two codes unique, deactivated too."""

    __tablename__ = "cost_category"
    __table_args__ = (
        *bounded("code", CODE_LENGTH),
        *bounded("label", LABEL_LENGTH),
        *bounded("accounting_code", CODE_LENGTH),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    accounting_code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    cost_type_id: Mapped[UUID] = mapped_column(
        ForeignKey(CostType.id, ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool]


class HourlyRate(Audited):
    """The hourly rate of a category for a year, at most one (WF-REF-0050)."""

    __tablename__ = "hourly_rate"
    __table_args__ = (
        CheckConstraint(f"year BETWEEN {YEARS[0]} AND {YEARS[1]}", name="year_bound"),
        CheckConstraint("amount >= 0.01", name="amount_minimum"),
        # One rate per category and year, named after its first column by the convention.
        UniqueConstraint("cost_category_id", "year"),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    cost_category_id: Mapped[UUID] = mapped_column(ForeignKey(CostCategory.id, ondelete="RESTRICT"))
    year: Mapped[int] = mapped_column(SmallInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class ActualCostMapping(Audited):
    """The mapping of the extraction of the actual costs, a single row: its counter and audit.

    Its labels are rows of their own (``ActualCostMappingLabel``); empty at the bootstrap.
    """

    __tablename__ = "actual_cost_mapping"
    __table_args__ = (CheckConstraint(f"id = {SINGLE_ROW}", name="single_row"), counted())

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)


class ActualCostMappingLabel(Base):
    """A label of the mapping (WF-REF-0190): of a column read, or of a column kept.

    ``folded`` is the label as the import compares it — without case, accents, nor spaces at its
    ends —, unique over the whole mapping: no label doubles another. Replaced row by row when the
    mapping is written whole; the bounds on their number are the service's.
    """

    __tablename__ = "actual_cost_mapping_label"
    __table_args__ = (
        CheckConstraint(_in("kind", LABEL_KINDS), name="kind_known"),
        CheckConstraint(_in('"column"', SOURCE_COLUMNS), name="column_known"),
        CheckConstraint(
            "(\"column\" IS NOT NULL) = (kind = 'read')", name="column_of_a_label_read"
        ),
        *bounded("label", LABEL_LENGTH),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    # Null for a column kept.
    column: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(Text)
    folded: Mapped[str] = mapped_column(Text, unique=True)
