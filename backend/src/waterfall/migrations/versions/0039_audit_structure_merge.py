# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit names the merge of a differential as the contract does: ``structure_merge``.

The action kept its former name, ``amendment_merge`` (K-04), until the merge was served:
``mergeCostStructure`` inscribes it (US-2560/L2). The constraint ``action_known`` admits the name
of the contract in place of the former one, and the index of the rank of the action, by which
``listAuditEvents`` sorts, follows — written out here, as a migration does not read the code that
follows it. No entry is to take up: no merge was ever inscribed, the merge not being served before,
and the journal refuses any update of its entries.

Created in the transaction of the migration, not ``CONCURRENTLY``, as ``0037`` did. The descent
refuses the name of the contract again; it fails while the journal holds a merge.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_entry"
RANK_INDEX = "ix_audit_entry_action_rank"
ACTIONS = (
    "project_create",
    "revision_mark",
    "revision_abandon",
    "reference_designate",
    "structure_merge",
    "structure_abandon",
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
ACTIONS_BEFORE = tuple(
    "amendment_merge" if action == "structure_merge" else action for action in ACTIONS
)


def _in(values: tuple[str, ...]) -> str:
    return f"action IN ({', '.join(repr(value) for value in values)})"


def _rank(values: tuple[str, ...]) -> str:
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], action)"


def _replace(actions: tuple[str, ...]) -> None:
    constraint = op.f(f"ck_{TABLE}_action_known")
    op.drop_constraint(constraint, TABLE, type_="check")
    op.create_check_constraint(constraint, TABLE, _in(actions))
    op.drop_index(RANK_INDEX, table_name=TABLE)
    op.create_index(RANK_INDEX, TABLE, [sa.text(_rank(actions))])


def upgrade() -> None:
    """Name the merge of a differential as the contract does, ranked as it ranks it."""
    _replace(ACTIONS)


def downgrade() -> None:
    """Give it its former name again; fails if the journal holds a merge."""
    _replace(ACTIONS_BEFORE)
