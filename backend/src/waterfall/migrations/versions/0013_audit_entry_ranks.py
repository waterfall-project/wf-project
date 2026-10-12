# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit sorts its actions and the natures of its objects in the contract's order.

``listAuditEvents`` sorts the action and the nature of the object in the order of their
enumerations in the contract, not as texts (WF-IHM-0060): by their rank, an expression that an
index on the text does not serve. Each gets an index of its own, on the very expression the query
names (``ACTION_RANK``, ``OBJECT_KIND_RANK`` of ``waterfall.platform.audit``), written out here
as a migration does not read the code that follows it.

It sorts the author an account before the platform, then by its name — an account anonymised,
which has lost it, after the names (``ACTOR_ORDER``): the index on the name alone, which put the
platform and the anonymised accounts together, gives way to one on that order.

Created in the transaction of the migration, not ``CONCURRENTLY``: the journal ships in the same
version as this migration, and holds at most the inscriptions of an installation that has just
been made when it runs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
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
    "user_anonymize",
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


ACTOR_NAME_INDEX = "ix_audit_entry_actor_display_name"
ACTOR_ORDER_INDEX = "ix_audit_entry_actor_order"


def upgrade() -> None:
    """Index the ranks of the action and of the nature of the object, and the author's order."""
    for name, (column, values) in RANKS.items():
        op.create_index(name, TABLE, [sa.text(_rank(column, values))])
    op.drop_index(ACTOR_NAME_INDEX, table_name=TABLE)
    op.create_index(
        ACTOR_ORDER_INDEX, TABLE, [sa.text("(actor_user_id IS NULL)"), "actor_display_name"]
    )


def downgrade() -> None:
    """Drop the three indexes, and index the name of the author alone again, as ``0003`` did."""
    op.drop_index(ACTOR_ORDER_INDEX, table_name=TABLE)
    op.create_index(ACTOR_NAME_INDEX, TABLE, ["actor_display_name"])
    for name in RANKS:
        op.drop_index(name, table_name=TABLE)
