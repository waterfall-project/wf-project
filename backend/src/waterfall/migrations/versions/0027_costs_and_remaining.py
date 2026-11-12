# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs and the remaining to commit (§4.4.1; EP-09, "Tables et migrations").

``estimate_line`` receives what a review of the project writes on a line: the figures and the
reestimated amount of the remaining to commit before it (``previous_*``), the instant of its last
re-estimation, the mark an amendment spares (EP-08), and the reason sent with it. They are added to
the partitioned table, which gives them to each partition; they are born null, and no row is to take
up. The guard of the estimate (migration 0025) refuses any write of a line of a marked revision,
whatever its columns: it protects them without changing.

Two tables of the regime "project", not partitioned: ``cost_line``, a line of the actual costs of a
project, unique by its document and its item, a null item a value like any other (WF-DAT-0110,
WF-INTF-0140), and ``cost_import``, the log of the imports that wrote them, never changed. Every key
refuses: a line of cost is never deleted, an entry of the log neither. A line names its subproject
with its project. The service may read, insert and change a line — an import
updates it, an exclusion too —, and read and insert an entry of the log.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The figures of the remaining to commit before the review, each never negative, as on the line.
PREVIOUS = (
    ("previous_quantity", sa.Numeric(14, 4)),
    ("previous_hours", sa.Numeric(12, 2)),
    ("previous_unit_disbursement", sa.Numeric(14, 2)),
    ("previous_reestimated_amount", sa.Numeric(14, 2)),
)
COUNTS = ("created_count", "updated_count", "unchanged_count", "rejected_count")
# A JSON object whose values are texts, a JSON array whose elements are texts.
TEXTS_BY_NAME = (
    "jsonb_typeof({0}) = 'object' AND NOT jsonb_path_exists({0}, '$.* ? (@.type() != \"string\")')"
)
TEXTS_IN_ORDER = (
    "jsonb_typeof({0}) = 'array' AND NOT jsonb_path_exists({0}, '$[*] ? (@.type() != \"string\")')"
)


def grant(rights: str, table: str) -> str:
    """Give the grant of rights on a table to the role of the service of this database."""
    return f"""
DO $$
BEGIN
    EXECUTE format('GRANT {rights} ON {table} TO %I', current_database() || '_service');
END
$$
"""


def not_negative(column: str) -> sa.CheckConstraint:
    """Refuse a negative value of a column."""
    return sa.CheckConstraint(f"{column} >= 0", name=f"{column}_not_negative")


def upgrade() -> None:
    """Add the six columns of a line, create the two tables of the actual costs; grant them."""
    for column, kind in PREVIOUS:
        op.add_column("estimate_line", sa.Column(column, kind, nullable=True))
        op.create_check_constraint(f"{column}_not_negative", "estimate_line", f"{column} >= 0")
    op.add_column(
        "estimate_line", sa.Column("reestimated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("estimate_line", sa.Column("remaining_reason", sa.Text(), nullable=True))
    _imports()
    _lines()
    op.execute(grant("SELECT, INSERT, UPDATE", "cost_line"))
    op.execute(grant("SELECT, INSERT", "cost_import"))


def _imports() -> None:
    op.create_table(
        "cost_import",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("import_report_id", sa.Uuid(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=True),
        sa.Column("period_to", sa.Date(), nullable=True),
        *(sa.Column(count, sa.Integer(), nullable=False) for count in COUNTS),
        sa.Column("passthrough_columns", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["import_report_id"], ["import_report.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("period_from <= period_to", name="period_ordered"),
        *(not_negative(count) for count in COUNTS),
        sa.CheckConstraint(
            TEXTS_IN_ORDER.format("passthrough_columns"), name="passthrough_columns_texts"
        ),
        sa.UniqueConstraint("import_report_id"),
    )
    op.create_index(None, "cost_import", ["project_id", "imported_at"])


def _lines() -> None:
    op.create_table(
        "cost_line",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("subproject_id", sa.Uuid(), nullable=True),
        sa.Column("subproject_code", sa.Text(collation="C"), nullable=True),
        sa.Column("document_number", sa.Text(collation="C"), nullable=False),
        sa.Column("document_item", sa.Text(collation="C"), nullable=True),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_in_tracked_scope", sa.Boolean(), nullable=False),
        sa.Column("excluded_reason", sa.Text(collation="C"), nullable=True),
        sa.Column("passthrough", postgresql.JSONB(), nullable=False),
        sa.Column("last_import_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_id", "subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["last_import_id"], ["cost_import.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "char_length(document_number) BETWEEN 1 AND 200", name="document_number_length"
        ),
        sa.CheckConstraint("document_number ~ '\\S'", name="document_number_not_blank"),
        sa.CheckConstraint("char_length(subproject_code) <= 50", name="subproject_code_length"),
        sa.CheckConstraint(
            "excluded_reason IS NULL OR NOT is_in_tracked_scope",
            name="excluded_reason_when_excluded",
        ),
        sa.CheckConstraint(
            "subproject_id IS NULL OR subproject_code IS NOT NULL",
            name="subproject_code_when_imputed",
        ),
        sa.CheckConstraint(TEXTS_BY_NAME.format("passthrough"), name="passthrough_texts"),
        sa.UniqueConstraint(
            "project_id", "document_number", "document_item", postgresql_nulls_not_distinct=True
        ),
    )
    op.create_index(None, "cost_line", ["project_id", "document_date"])
    op.create_index(None, "cost_line", ["subproject_id", "project_id"])
    op.create_index(None, "cost_line", ["subproject_code", "project_id"])


def downgrade() -> None:
    """Drop the two tables and the six columns: their rows and values are lost."""
    op.drop_table("cost_line")
    op.drop_table("cost_import")
    op.drop_column("estimate_line", "remaining_reason")
    op.drop_column("estimate_line", "reestimated_at")
    for column, _ in reversed(PREVIOUS):
        op.drop_column("estimate_line", column)
