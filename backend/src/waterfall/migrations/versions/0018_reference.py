# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the reference (§4.4.1, regime "reference"; EP-05, "Tables et migrations").

The settings the installation shares and the units of duration, a single row each; the natures and
the categories of cost, the hourly rates; the tree of the organisation, the calendars and the roles
of resources; the mapping of the extraction of the actual costs, a single row, and its labels. The
single rows are the bootstrap's to write, never a migration's. Nothing here is deleted by the
service — an object is deactivated —, but a label of the mapping, which its whole writing replaces
row by row: the role of the service selects, inserts and updates each table, and deletes those
labels alone. Every key refuses (``RESTRICT``): the reference cascades nothing.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.schema import SchemaItem

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The tables in the order they are created, those another refers to first.
TABLES = (
    "reference_setting",
    "duration_unit",
    "cost_type",
    "cost_category",
    "hourly_rate",
    "org_node",
    "calendar",
    "resource_role",
    "actual_cost_mapping",
    "actual_cost_mapping_label",
)
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

GRANT = f"""
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE ON {", ".join(TABLES)} TO %I',
        current_database() || '_service'
    );
    EXECUTE format(
        'GRANT DELETE ON actual_cost_mapping_label TO %I', current_database() || '_service'
    );
END
$$
"""


def audited() -> list[SchemaItem]:
    """Give the counter of the writes and the columns of audit of a row that changes."""
    return [
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    ]


def bounded(column: str, longest: int) -> list[SchemaItem]:
    """Bound a text from 1 to ``longest`` characters, and refuse it blank."""
    return [
        sa.CheckConstraint(
            f"char_length({column}) BETWEEN 1 AND {longest}", name=f"{column}_length"
        ),
        sa.CheckConstraint(f"{column} ~ '\\S'", name=f"{column}_not_blank"),
    ]


def sorted_text(name: str) -> sa.Column[str]:
    """Give a text column a table sorts, in the order of the code points."""
    return sa.Column(name, sa.Text(collation="C"), nullable=False)


def upgrade() -> None:
    """Create the ten tables, and grant the service what it needs on each."""
    _cost_settings()
    _resource_settings()
    _mapping()
    op.execute(GRANT)


def _cost_settings() -> None:
    thresholds = ("cost_watch", "cost_alert", "schedule_watch", "schedule_alert")
    op.create_table(
        "reference_setting",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("currency_code", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        *(
            sa.Column(f"{axis}_bound_{rank}", sa.Numeric(), nullable=False)
            for axis in ("probability", "severity")
            for rank in (1, 2, 3)
        ),
        sa.Column("risk_zones", postgresql.ARRAY(sa.Text()), nullable=False),
        *(sa.Column(threshold, sa.Numeric(), nullable=False) for threshold in thresholds),
        sa.Column("max_weeks_between_reviews", sa.SmallInteger(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_form"),
        *bounded("company_name", 200),
        sa.CheckConstraint(
            "probability_bound_1 < probability_bound_2 "
            "AND probability_bound_2 < probability_bound_3",
            name="probability_bounds_increasing",
        ),
        sa.CheckConstraint(
            "severity_bound_1 < severity_bound_2 AND severity_bound_2 < severity_bound_3",
            name="severity_bounds_increasing",
        ),
        sa.CheckConstraint(
            "array_ndims(risk_zones) = 1 AND cardinality(risk_zones) = 16",
            name="risk_zones_sixteen",
        ),
        sa.CheckConstraint(
            "risk_zones <@ ARRAY['nominal', 'watch', 'alert']", name="risk_zones_known"
        ),
        sa.CheckConstraint(
            " AND ".join(f"{threshold} > 0 AND {threshold} < 1" for threshold in thresholds),
            name="thresholds_between_zero_and_one",
        ),
        sa.CheckConstraint(
            "cost_alert < cost_watch AND schedule_alert < schedule_watch", name="alert_below_watch"
        ),
        sa.CheckConstraint(
            "max_weeks_between_reviews BETWEEN 1 AND 104", name="max_weeks_between_reviews_bound"
        ),
    )
    op.create_table(
        "cost_type",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("code"),
        sorted_text("label"),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        *bounded("code", 20),
        *bounded("label", 200),
        sa.CheckConstraint("kind IN ('labor', 'non_labor', 'provision')", name="kind_known"),
    )
    op.create_table(
        "cost_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("code"),
        sorted_text("label"),
        sorted_text("accounting_code"),
        sa.Column("cost_type_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("accounting_code"),
        sa.ForeignKeyConstraint(["cost_type_id"], ["cost_type.id"], ondelete="RESTRICT"),
        *bounded("code", 20),
        *bounded("label", 200),
        *bounded("accounting_code", 20),
    )
    op.create_index(None, "cost_category", ["cost_type_id"])
    op.create_table(
        "hourly_rate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cost_category_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cost_category_id", "year"),
        sa.ForeignKeyConstraint(["cost_category_id"], ["cost_category.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("year BETWEEN 2000 AND 2100", name="year_bound"),
        sa.CheckConstraint("amount >= 0.01", name="amount_minimum"),
    )


def _resource_settings() -> None:
    op.create_table(
        "duration_unit",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("hours_per_day", sa.Numeric(), nullable=False),
        sa.Column("hours_per_week", sa.Numeric(), nullable=False),
        sa.Column("days_per_month", sa.Numeric(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        sa.CheckConstraint(
            "hours_per_day > 0 AND hours_per_week > 0 AND days_per_month > 0",
            name="constants_positive",
        ),
    )
    op.create_table(
        "org_node",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("code"),
        sorted_text("label"),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["parent_id"], ["org_node.id"], ondelete="RESTRICT"),
        *bounded("code", 20),
        *bounded("label", 200),
        sa.CheckConstraint("parent_id <> id", name="not_its_own_parent"),
    )
    op.create_index(None, "org_node", ["parent_id"])
    op.create_table(
        "calendar",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("label"),
        *(sa.Column(day, sa.Numeric(4, 2), nullable=False) for day in DAYS),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("label"),
        *bounded("label", 200),
        sa.CheckConstraint(
            " AND ".join(f"{day} BETWEEN 0 AND 24" for day in DAYS), name="hours_of_a_day"
        ),
        sa.CheckConstraint("is_active OR NOT is_default", name="default_active"),
    )
    op.create_index(
        "uq_calendar_default",
        "calendar",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_table(
        "resource_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("code"),
        sorted_text("label"),
        sa.Column("org_node_id", sa.Uuid(), nullable=False),
        sa.Column("cost_category_id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=False),
        sa.Column("monthly_hours", sa.Numeric(), nullable=False),
        sa.Column("headcount", sa.Numeric(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["org_node_id"], ["org_node.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cost_category_id"], ["cost_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["calendar_id"], ["calendar.id"], ondelete="RESTRICT"),
        *bounded("code", 20),
        *bounded("label", 200),
        sa.CheckConstraint("monthly_hours >= 0", name="monthly_hours_not_negative"),
        sa.CheckConstraint("headcount >= 0", name="headcount_not_negative"),
    )
    for column in ("org_node_id", "cost_category_id", "calendar_id"):
        op.create_index(None, "resource_role", [column])


def _mapping() -> None:
    op.create_table(
        "actual_cost_mapping",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
    )
    op.create_table(
        "actual_cost_mapping_label",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("column", sa.Text(), nullable=True),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("folded", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folded"),
        sa.CheckConstraint("kind IN ('read', 'kept')", name="kind_known"),
        sa.CheckConstraint(
            "\"column\" IN ('wbs_element', 'document_number', 'document_item', 'document_date', "
            "'amount')",
            name="column_known",
        ),
        sa.CheckConstraint(
            "(\"column\" IS NOT NULL) = (kind = 'read')", name="column_of_a_label_read"
        ),
        *bounded("label", 200),
    )


def downgrade() -> None:
    """Drop the ten tables, with their rights: the reference they held is lost."""
    for table in reversed(TABLES):
        op.drop_table(table)
