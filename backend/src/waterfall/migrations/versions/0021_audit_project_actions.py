# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit knows the creation of a project and the abandonment of a revision.

WF-SEC-0030 names both among the actions it inscribes, and the contract frozen at 1.0.0 carries
them (``AuditAction``, #1577): the constraint ``action_known`` admits them, and the index of the
rank of the action, by which ``listAuditEvents`` sorts, follows the order of the contract — written
out here, as a migration does not read the code that follows it. The merge of a differential keeps
its former name (K-04).

The constraint ``object_labeled`` admits as well a null label for the action ``revision_abandon``
alone: the contract inscribes the abandonment of a revision, which is deleted, without its label
(``audit_events_revision_abandoned``, #2161). The condition names the action, not every object of
the nature ``revision``, so that no other inscription of a revision loses its label.

The constraint ``project_named`` names a project by its identifier and its label, and admits its
code null: a project is born without code, which it bears from the state In progress on
(WF-PRJ-0010), and its creation and the abandonment of its revision are inscribed before (#2166).
A code without a project stays refused.

Created in the transaction of the migration, not ``CONCURRENTLY``: the journal holds at most the
inscriptions of the platform and of its accounts when it runs.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_entry"
RANK_INDEX = "ix_audit_entry_action_rank"
NEW = ("project_create", "revision_abandon")
ACTIONS = (
    "project_create",
    "revision_mark",
    "revision_abandon",
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
ACTIONS_BEFORE = tuple(action for action in ACTIONS if action not in NEW)
LABELED = (
    "object_label IS NOT NULL OR object_kind IN ('backup', 'user')",
    (
        "object_label IS NOT NULL OR object_kind IN ('backup', 'user') "
        "OR action IN ('revision_abandon')"
    ),
)


NAMED = (
    (
        "(project_id IS NULL) = (project_code IS NULL) "
        "AND (project_id IS NULL) = (project_label IS NULL)"
    ),
    (
        "(project_id IS NULL) = (project_label IS NULL) "
        "AND (project_id IS NOT NULL OR project_code IS NULL)"
    ),
)


def _in(values: tuple[str, ...]) -> str:
    return f"action IN ({', '.join(repr(value) for value in values)})"


def _rank(values: tuple[str, ...]) -> str:
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], action)"


def _replace(actions: tuple[str, ...], labeled: str, named: str) -> None:
    constraint = op.f(f"ck_{TABLE}_action_known")
    op.drop_constraint(constraint, TABLE, type_="check")
    op.create_check_constraint(constraint, TABLE, _in(actions))
    op.drop_index(RANK_INDEX, table_name=TABLE)
    op.create_index(RANK_INDEX, TABLE, [sa.text(_rank(actions))])
    labeled_name = op.f(f"ck_{TABLE}_object_labeled")
    op.drop_constraint(labeled_name, TABLE, type_="check")
    op.create_check_constraint(labeled_name, TABLE, labeled)
    named_name = op.f(f"ck_{TABLE}_project_named")
    op.drop_constraint(named_name, TABLE, type_="check")
    op.create_check_constraint(named_name, TABLE, named)


def upgrade() -> None:
    """Admit the two actions, ranked as the contract, a nameless abandonment, a codeless project."""
    _replace(ACTIONS, LABELED[1], NAMED[1])


def downgrade() -> None:
    """Refuse the two actions, a null label, a codeless project; fails if the journal holds one."""
    _replace(ACTIONS_BEFORE, LABELED[0], NAMED[0])
