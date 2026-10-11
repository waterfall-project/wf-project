# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit sorts its actions and the natures of its objects in the contract's order.

``listAuditEvents`` sorts the action and the nature of the object in the order of their
enumerations in the contract, not as texts (WF-IHM-0060): by their rank, an expression that an
index on the text does not serve. Each gets an index of its own, on the very expression the query
names (``ACTION_RANK``, ``OBJECT_KIND_RANK`` of ``waterfall.platform.audit``), written out here
as a migration does not read the code that follows it.

Created in the transaction of the migration, not ``CONCURRENTLY``: the journal ships in the same
version as this migration, and holds at most the inscriptions of an installation that has just
been made when it runs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_entry"
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
RANKS = {
    "ix_audit_entry_action_rank": ("action", ACTIONS),
    "ix_audit_entry_object_kind_rank": ("object_kind", OBJECT_KINDS),
}


def _rank(column: str, values: tuple[str, ...]) -> str:
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], {column})"


def upgrade() -> None:
    """Index the rank of the action and that of the nature of the object."""
    for name, (column, values) in RANKS.items():
        op.create_index(name, TABLE, [sa.text(_rank(column, values))])


def downgrade() -> None:
    """Drop the two indexes; the journal sorts as before, without them."""
    for name in RANKS:
        op.drop_index(name, table_name=TABLE)
