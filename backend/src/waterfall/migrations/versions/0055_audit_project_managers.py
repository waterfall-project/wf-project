# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit knows the project managers; the contributors bear their columns of audit.

The specification 1.0.7 adds to WF-SEC-0030 the registration, the removal and the change of
capacity of a project manager, and the contract names them since US-2980/L1 (``AuditAction``,
``AuditObjectKind``, #4127): the constraint ``action_known`` admits the three actions, after the
exit of a project, and ``object_kind_known`` the contributor, after the risk; the indexes of their
ranks, by which ``listAuditEvents`` sorts, follow the order of the contract — written out here, as
a migration does not read the code that follows it.

A contributor is named by its account, whose anonymisation forgets the name (WF-ADM-0060): the
constraint ``object_labeled`` admits it without a label, and the two triggers of the journal let
the service make null the label of a contributor as of an account — the journal's, that the label
alone changes; the accounts', that its account is anonymised (``0011``).

Two composite indexes serve the latest inscription of each author and of each project, which the
facets read, and the journal of one of them in its own order (#934). Created in the transaction of
the migration, not ``CONCURRENTLY``, as ``0037`` did: the journal of an installation is small.

The table ``contributor`` receives its columns of audit (WF-DAT-0070, #3988): the dates by default
the moment of the write, so that the code before this migration, which writes none, still writes a
line during an update (WF-DAT-0140), and a line there is dated by the migration, by the platform —
its authors null —, no one knowing who wrote it before.

The descent drops the columns of the contributors, losing them, and refuses again the three actions
and the contributor; it fails while the journal holds one.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from uuid import UUID

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_entry"
CONTRIBUTOR = "contributor"
NEW_ACTIONS = ("project_manager_add", "project_manager_remove", "project_manager_change")
ACTIONS = (
    "project_create",
    "revision_mark",
    "revision_abandon",
    "reference_designate",
    "structure_merge",
    "structure_abandon",
    "risk_occurrence",
    "project_exit",
    *NEW_ACTIONS,
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
ACTIONS_BEFORE = tuple(action for action in ACTIONS if action not in NEW_ACTIONS)
OBJECT_KINDS = (
    "project",
    "revision",
    "cost_structure",
    "risk",
    CONTRIBUTOR,
    "cost_line",
    "import",
    "user",
    "access_role",
    "backup",
    "external_backup_upload",
)
OBJECT_KINDS_BEFORE = tuple(kind for kind in OBJECT_KINDS if kind != CONTRIBUTOR)
# The natures named by an account, whose label an anonymisation forgets, before and after.
ACCOUNT_KINDS = ("('user')", "('user', 'contributor')")
LABELED = tuple(
    f"object_label IS NOT NULL OR object_kind IN ('backup', {kinds[1:]} "
    "OR action IN ('revision_abandon')"
    for kinds in ACCOUNT_KINDS
)

# The update the trigger of the journal admits, as ``0011`` wrote it, the natures of an account
# formatted in: each label of an account kept or made null, one of them at least made null,
# nothing else changed.
GUARD = """
CREATE OR REPLACE FUNCTION audit_entry_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF (NEW.actor_display_name IS NOT DISTINCT FROM OLD.actor_display_name
                OR (NEW.actor_display_name IS NULL AND OLD.actor_user_id IS NOT NULL))
            AND (NEW.object_label IS NOT DISTINCT FROM OLD.object_label
                OR (NEW.object_label IS NULL AND OLD.object_kind IN {kinds}))
            AND (NEW.actor_display_name IS DISTINCT FROM OLD.actor_display_name
                OR NEW.object_label IS DISTINCT FROM OLD.object_label)
            AND to_jsonb(NEW) - 'actor_display_name' - 'object_label'
                = to_jsonb(OLD) - 'actor_display_name' - 'object_label'
        THEN
            RETURN NEW;
        END IF;
    END IF;
    RAISE EXCEPTION 'audit_entry is never updated nor deleted: % refused', TG_OP
        USING ERRCODE = 'restrict_violation';
END
$$
"""

# The trigger of the module of the accounts on the journal, as ``0011`` wrote it, the natures of an
# account formatted in: a label made null names an anonymised account.
FORGET_ANONYMIZED = """
CREATE OR REPLACE FUNCTION user_account_forget_anonymized() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.actor_display_name IS NULL AND OLD.actor_display_name IS NOT NULL
            AND NOT EXISTS (
                SELECT FROM user_account
                WHERE id = OLD.actor_user_id AND anonymized_at IS NOT NULL
            ))
        OR (NEW.object_label IS NULL AND OLD.object_label IS NOT NULL
            AND NOT (OLD.object_kind IN {kinds} AND EXISTS (
                SELECT FROM user_account
                WHERE id = OLD.object_id AND anonymized_at IS NOT NULL
            )))
    THEN
        RAISE EXCEPTION 'audit_entry forgets the name of an anonymised account alone: % refused',
            TG_OP USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END
$$
"""

LATEST_INDEXES = {
    "ix_audit_entry_actor_latest": "actor_user_id",
    "ix_audit_entry_project_latest": "project_id",
}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _rank(column: str, values: tuple[str, ...]) -> str:
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], {column})"


def _replace_check(name: str, condition: str) -> None:
    constraint = op.f(f"ck_{TABLE}_{name}")
    op.drop_constraint(constraint, TABLE, type_="check")
    op.create_check_constraint(constraint, TABLE, condition)


def _replace_rank(column: str, values: tuple[str, ...]) -> None:
    index = f"ix_{TABLE}_{column}_rank"
    op.drop_index(index, table_name=TABLE)
    op.create_index(index, TABLE, [sa.text(_rank(column, values))])


def _journal(actions: tuple[str, ...], kinds: tuple[str, ...], step: int) -> None:
    """Write the enumerations, their ranks, the labels and the triggers of the journal."""
    _replace_check("action_known", _in("action", actions))
    _replace_check("object_kind_known", _in("object_kind", kinds))
    _replace_check("object_labeled", LABELED[step])
    _replace_rank("action", actions)
    _replace_rank("object_kind", kinds)
    op.execute(GUARD.format(kinds=ACCOUNT_KINDS[step]))
    op.execute(FORGET_ANONYMIZED.format(kinds=ACCOUNT_KINDS[step]))


def _author(name: str) -> sa.Column[UUID]:
    return sa.Column(
        name,
        sa.Uuid(),
        sa.ForeignKey(
            "user_account.id",
            name=op.f(f"fk_{CONTRIBUTOR}_{name}_user_account"),
            ondelete="RESTRICT",
        ),
        nullable=True,
    )


def _dated(name: str) -> sa.Column[datetime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    """Admit the three actions and the contributor, index the latest, stamp the contributors."""
    _journal(ACTIONS, OBJECT_KINDS, 1)
    for name, column in LATEST_INDEXES.items():
        op.create_index(name, TABLE, [column, sa.text("occurred_at DESC"), sa.text("id DESC")])
    op.add_column(CONTRIBUTOR, _dated("created_at"))
    op.add_column(CONTRIBUTOR, _author("created_by"))
    op.add_column(CONTRIBUTOR, _dated("updated_at"))
    op.add_column(CONTRIBUTOR, _author("updated_by"))


def downgrade() -> None:
    """Drop the columns of the contributors and the indexes; refuse the actions and the nature.

    The columns of audit of the contributors are lost; fails while the journal holds one of the
    three actions or a contributor.
    """
    for name in ("updated_by", "updated_at", "created_by", "created_at"):
        op.drop_column(CONTRIBUTOR, name)
    for name in LATEST_INDEXES:
        op.drop_index(name, table_name=TABLE)
    _journal(ACTIONS_BEFORE, OBJECT_KINDS_BEFORE, 0)
