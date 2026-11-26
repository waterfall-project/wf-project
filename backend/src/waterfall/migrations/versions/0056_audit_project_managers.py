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
facets read, and the journal of one of them in its own order (#934).

The journal is the table the US takes to its volumes, which every action writes and nothing purges:
no lock that stops its writes is held while it is read (``docs/dev/sql.md``, rule 6), unlike
``0037`` before. The upgrade goes in four steps. Out of any transaction (``autocommit_block``,
which commits the migrations applied before), the two indexes and the ranks in their new order —
under a name of their own — are created ``CONCURRENTLY``, each dropped first if a stopped run left
it invalid. Then a transaction poses the three checks ``NOT VALID``, which takes the exclusive
lock of the table without reading it, and commits; out of it again, each is validated, reading
the table under a lock that lets the writes go. Last, the transaction the migration is stamped in
drops the former ranks, renames the new ones, writes the triggers and stamps the contributors,
reading no row of the journal. Each step runs again if a later one stopped: the version stays
``0055`` until the last, and the checks posed before it only widen.

The table ``contributor`` receives its columns of audit (WF-DAT-0070, #3988): the dates by default
the moment of the write, so that the code before this migration, which writes none, still writes a
line during an update (WF-DAT-0140), and a line there is dated by the migration, by the platform —
its authors null —, no one knowing who wrote it before.

The descent drops the columns of the contributors, losing them, and refuses again the three actions
and the contributor; it fails while the journal holds one. It runs in one transaction, its checks
validated at once and its ranks created in it: it never runs on an installation
(``runner.downgrade``), and it must fail whole — a check validated apart would refuse once the rest
of the descent was committed.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from uuid import UUID

revision: str = "0056"
down_revision: str | None = "0055"
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
RANKED = ("action", "object_kind")
CHECKS = ("action_known", "object_kind_known", "object_labeled")
# The name a rank in its new order is created under, beside the former one it replaces.
NEXT = "_next"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _rank(column: str, values: tuple[str, ...]) -> str:
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], {column})"


def _rank_index(column: str) -> str:
    return f"ix_{TABLE}_{column}_rank"


def _conditions(actions: tuple[str, ...], kinds: tuple[str, ...], step: int) -> dict[str, str]:
    """Give the condition of each check of the journal, by its name."""
    return dict(
        zip(
            CHECKS,
            (_in("action", actions), _in("object_kind", kinds), LABELED[step]),
            strict=True,
        )
    )


def _replace_checks(conditions: dict[str, str], *, not_valid: bool) -> None:
    for name, condition in conditions.items():
        constraint = op.f(f"ck_{TABLE}_{name}")
        op.drop_constraint(constraint, TABLE, type_="check")
        op.create_check_constraint(constraint, TABLE, condition, postgresql_not_valid=not_valid)


def _triggers(step: int) -> None:
    op.execute(GUARD.format(kinds=ACCOUNT_KINDS[step]))
    op.execute(FORGET_ANONYMIZED.format(kinds=ACCOUNT_KINDS[step]))


def _create_concurrently(name: str, columns: list[str | sa.TextClause]) -> None:
    """Create an index without stopping the writes, an invalid one a stopped run left dropped."""
    op.drop_index(name, table_name=TABLE, postgresql_concurrently=True, if_exists=True)
    op.create_index(name, TABLE, columns, postgresql_concurrently=True)


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
    """Admit the three actions and the contributor, index the latest, stamp the contributors.

    No lock that stops the writes of the journal is held while it is read: the indexes are created
    ``CONCURRENTLY`` and the checks validated apart, each out of a transaction.
    """
    ranks = {"action": ACTIONS, "object_kind": OBJECT_KINDS}
    context = op.get_context()
    with context.autocommit_block():
        for name, column in LATEST_INDEXES.items():
            _create_concurrently(name, [column, sa.text("occurred_at DESC"), sa.text("id DESC")])
        for column in RANKED:
            _create_concurrently(
                _rank_index(column) + NEXT, [sa.text(_rank(column, ranks[column]))]
            )
    _replace_checks(_conditions(ACTIONS, OBJECT_KINDS, 1), not_valid=True)
    with context.autocommit_block():
        for name in CHECKS:
            op.execute(f"ALTER TABLE {TABLE} VALIDATE CONSTRAINT ck_{TABLE}_{name}")
    for column in RANKED:
        op.drop_index(_rank_index(column), table_name=TABLE)
        op.execute(f"ALTER INDEX {_rank_index(column) + NEXT} RENAME TO {_rank_index(column)}")
    _triggers(1)
    op.add_column(CONTRIBUTOR, _dated("created_at"))
    op.add_column(CONTRIBUTOR, _author("created_by"))
    op.add_column(CONTRIBUTOR, _dated("updated_at"))
    op.add_column(CONTRIBUTOR, _author("updated_by"))


def downgrade() -> None:
    """Drop the columns of the contributors and the indexes; refuse the actions and the nature.

    The columns of audit of the contributors are lost; fails while the journal holds one of the
    three actions or a contributor, in one transaction that leaves the schema as it was.
    """
    for name in ("updated_by", "updated_at", "created_by", "created_at"):
        op.drop_column(CONTRIBUTOR, name)
    for name in LATEST_INDEXES:
        op.drop_index(name, table_name=TABLE)
    _replace_checks(_conditions(ACTIONS_BEFORE, OBJECT_KINDS_BEFORE, 0), not_valid=False)
    ranks = {"action": ACTIONS_BEFORE, "object_kind": OBJECT_KINDS_BEFORE}
    for column in RANKED:
        op.drop_index(_rank_index(column), table_name=TABLE)
        op.create_index(_rank_index(column), TABLE, [sa.text(_rank(column, ranks[column]))])
    _triggers(0)
