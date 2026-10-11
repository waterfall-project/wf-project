# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The anonymisation of an account, and the one change the journal of audit admits for it.

An anonymised account keeps its row: its name, its first name and its address become null, which
they are for an anonymised account alone, and so does its avatar; ``anonymized_at`` says when,
and an anonymised account stays deactivated (WF-ADM-0060). The index of the addresses admits
several null ones.

The journal refuses any change of an inscription but one: the label that names an account — as
its author, or as its object — becomes null, the rest of the row unchanged (WF-SEC-0030). The
trigger compares the whole row but those two labels, so that a column added later is kept as
well; the role of the service may update those two columns, and no other. That the account is
anonymised is the journal's caller's to know: the trigger reads no table of another module.
``user_anonymize`` joins the actions of the journal.

The descent restores what ``0003`` and ``0001`` declared: it is refused by the database once an
account has been anonymised, whose names are lost.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCOUNT = "user_account"
JOURNAL = "audit_entry"
IDENTITY = ("last_name", "first_name", "email")
ACTIONS_BEFORE = (
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
ACTIONS = (*ACTIONS_BEFORE[:12], "user_anonymize", *ACTIONS_BEFORE[12:])

# Each name null for an anonymised account, and for it alone.
IDENTITY_UNLESS_ANONYMIZED = " AND ".join(
    f"(anonymized_at IS NULL) = ({name} IS NOT NULL)" for name in IDENTITY
)
ANONYMIZED_DEACTIVATED = "anonymized_at IS NULL OR (state = 'deactivated' AND avatar IS NULL)"

# The checks of the journal this migration loosens, before and after: an account may have lost its
# name; the platform never has one.
ACTOR_NAMED = (
    "(actor_user_id IS NULL) = (actor_display_name IS NULL)",
    "actor_user_id IS NOT NULL OR actor_display_name IS NULL",
)
OBJECT_LABELED = (
    "object_label IS NOT NULL OR object_kind = 'backup'",
    "object_label IS NOT NULL OR object_kind IN ('backup', 'user')",
)

# The update the trigger admits: each label of an account kept or made null, nothing else changed.
GUARD = """
CREATE OR REPLACE FUNCTION audit_entry_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF (NEW.actor_display_name IS NOT DISTINCT FROM OLD.actor_display_name
                OR (NEW.actor_display_name IS NULL AND OLD.actor_user_id IS NOT NULL))
            AND (NEW.object_label IS NOT DISTINCT FROM OLD.object_label
                OR (NEW.object_label IS NULL AND OLD.object_kind = 'user'))
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

# The function of ``0003``, which refuses every change.
REFUSE = """
CREATE OR REPLACE FUNCTION audit_entry_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_entry is never updated nor deleted: % refused', TG_OP
        USING ERRCODE = 'restrict_violation';
END
$$
"""

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        '{verb} UPDATE (actor_display_name, object_label) ON audit_entry {way} %I',
        current_database() || '_service'
    );
END
$$
"""


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _replace_check(table: str, name: str, condition: str) -> None:
    constraint = op.f(f"ck_{table}_{name}")
    op.drop_constraint(constraint, table, type_="check")
    op.create_check_constraint(constraint, table, condition)


def upgrade() -> None:
    """Let an account be anonymised, and the journal forget its name."""
    op.add_column(ACCOUNT, sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))
    for name in IDENTITY:
        op.alter_column(ACCOUNT, name, existing_type=sa.Text(collation="C"), nullable=True)
    op.create_check_constraint(
        op.f("ck_user_account_identity_unless_anonymized"), ACCOUNT, IDENTITY_UNLESS_ANONYMIZED
    )
    op.create_check_constraint(
        op.f("ck_user_account_anonymized_deactivated"), ACCOUNT, ANONYMIZED_DEACTIVATED
    )
    _replace_check(JOURNAL, "action_known", _in("action", ACTIONS))
    _replace_check(JOURNAL, "actor_named", ACTOR_NAMED[1])
    _replace_check(JOURNAL, "object_labeled", OBJECT_LABELED[1])
    op.execute(GUARD)
    op.execute(GRANT.format(verb="GRANT", way="TO"))


def downgrade() -> None:
    """Refuse again every change of the journal, and give every account back its names."""
    op.execute(GRANT.format(verb="REVOKE", way="FROM"))
    op.execute(REFUSE)
    _replace_check(JOURNAL, "object_labeled", OBJECT_LABELED[0])
    _replace_check(JOURNAL, "actor_named", ACTOR_NAMED[0])
    _replace_check(JOURNAL, "action_known", _in("action", ACTIONS_BEFORE))
    op.drop_constraint(op.f("ck_user_account_anonymized_deactivated"), ACCOUNT, type_="check")
    op.drop_constraint(op.f("ck_user_account_identity_unless_anonymized"), ACCOUNT, type_="check")
    for name in IDENTITY:
        op.alter_column(ACCOUNT, name, existing_type=sa.Text(collation="C"), nullable=False)
    op.drop_column(ACCOUNT, "anonymized_at")
