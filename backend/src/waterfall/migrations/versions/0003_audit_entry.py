# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit: its table, which no one updates nor deletes from (WF-SEC-0030).

Written by hand from ``waterfall.platform.audit``, which a test compares with what this
migration builds. The role of the service has ``INSERT`` and ``SELECT`` on the table and nothing
else; a trigger refuses an update, a deletion or a truncation to whoever asks, the owner of the
table included. The identifiers of the author, the object and the project are no foreign keys:
an inscription outlives what it names (WF-DAT-0090).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIONS = (
    "revision_mark",
    "reference_designate",
    "amendment_merge",
    "risk_occurrence",
    "project_exit",
    "cost_line_exclude",
    "cost_line_reinstate",
    "import_apply",
    "user_create",
    "user_update",
    "user_deactivate",
    "user_reactivate",
    "password_link_create",
    "access_role_create",
    "access_role_update",
    "access_role_delete",
    "user_access_roles_set",
    "backup",
    "restore",
)
OBJECT_KINDS = (
    "project",
    "revision",
    "cost_structure",
    "risk",
    "cost_line",
    "import",
    "user",
    "access_role",
    "backup",
    "external_backup_upload",
)
INDEXED = (
    "occurred_at",
    "actor_user_id",
    "actor_display_name",
    "action",
    "object_kind",
    "object_id",
    "object_label",
    "project_id",
    "project_code",
    "correlation_id",
)

# The refusal names the table and the operation: the code that a test, and a reader of the logs
# of the database, recognize. The truncation is refused by a trigger of its own, per statement.
REFUSE = """
CREATE FUNCTION audit_entry_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_entry is never updated nor deleted: % refused', TG_OP
        USING ERRCODE = 'restrict_violation';
END
$$
"""

# The role of the service of this database (migration ``0002``) reads and inscribes, nothing more.
GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT SELECT, INSERT ON audit_entry TO %I', current_database() || '_service');
END
$$
"""


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    """Create the table, its indexes, the triggers that refuse a change, and grant the service."""
    op.create_table(
        "audit_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_display_name", sa.Text(collation="C"), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("object_kind", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("object_label", sa.Text(collation="C"), nullable=True),
        sa.Column("object_revision_id", sa.Uuid(), nullable=True),
        sa.Column("object_revision_label", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("project_code", sa.Text(collation="C"), nullable=True),
        sa.Column("project_label", sa.Text(), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_id", sa.Text(collation="C"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(_in("action", ACTIONS), name="action_known"),
        sa.CheckConstraint(_in("object_kind", OBJECT_KINDS), name="object_kind_known"),
        sa.CheckConstraint(
            "(actor_user_id IS NULL) = (actor_display_name IS NULL)", name="actor_named"
        ),
        sa.CheckConstraint(
            "(project_id IS NULL) = (project_code IS NULL) "
            "AND (project_id IS NULL) = (project_label IS NULL)",
            name="project_named",
        ),
        sa.CheckConstraint(
            "object_label IS NOT NULL OR object_kind = 'backup'", name="object_labeled"
        ),
        sa.CheckConstraint(
            "object_revision_id IS NOT NULL OR object_revision_label IS NULL",
            name="object_revision_named",
        ),
        sa.CheckConstraint("jsonb_typeof(params) = 'object'", name="params_object"),
        sa.CheckConstraint("correlation_id ~ '^[A-Za-z0-9._-]{1,64}$'", name="correlation_id_form"),
    )
    for column in INDEXED:
        op.create_index(None, "audit_entry", [column])
    op.execute(REFUSE)
    op.execute(
        "CREATE TRIGGER audit_entry_refuse_row_change BEFORE UPDATE OR DELETE ON audit_entry "
        "FOR EACH ROW EXECUTE FUNCTION audit_entry_refuse_change()"
    )
    op.execute(
        "CREATE TRIGGER audit_entry_refuse_truncate BEFORE TRUNCATE ON audit_entry "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_entry_refuse_change()"
    )
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table, its triggers and their function: every inscription is lost with them."""
    op.drop_table("audit_entry")
    op.execute("DROP FUNCTION audit_entry_refuse_change()")
