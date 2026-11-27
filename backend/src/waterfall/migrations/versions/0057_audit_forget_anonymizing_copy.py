# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal forgets the name of any account when a copy of the production is anonymised.

``waterfall-restore anonymize`` (US-2960, #4068) keeps the administrators of the copy active, under
an identity in the reserved domain, and not anonymised, lest nobody enter the copy (WF-ADM-0120):
the trigger of the module of the accounts, ``user_account_forget_anonymized`` (``0011``, rewritten
by ``0056``), which lets the journal forget the name of an anonymised account alone, refused to
forget theirs, and the command failed on every real copy, where they are named as authors and as
objects (decision of the author of 2026-11-27, option A).

The trigger now lets the journal forget the name of any account in a transaction that posed
``SET LOCAL waterfall.anonymizing_copy = 'on'``, and only when the role signed in — and the role
in force — is the owner of the journal. The command signs in as the owner of the tables (the
service of the restoration, ``waterfall``), the API and the worker as the role of the service
(``waterfall_service``), which may pose a setting of its own as any role may: the setting alone
would open the trigger to them. The role signed in (``session_user``) is checked besides the role
in force (``current_user``), which a function ``SECURITY DEFINER`` of the owner — such as
``reserve_project_partitions``, ``0055`` — would make the owner's within a session of the service.
Elsewhere, the guarantee does not change: the owner too, without the setting, forgets the name of
an anonymised account alone; and the trigger of the journal, which fires first, still refuses any
change but a label of an account made null (``audit_entry_refuse_change``). What ``0056`` added —
the contributor, named by its account — is kept.

The descent writes the trigger back as ``0056`` left it.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The trigger as ``0056`` wrote it: a label made null names an anonymised account.
FORGET_ANONYMIZED = """
CREATE OR REPLACE FUNCTION user_account_forget_anonymized() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.actor_display_name IS NULL AND OLD.actor_display_name IS NOT NULL
            AND NOT EXISTS (
                SELECT FROM user_account
                WHERE id = OLD.actor_user_id AND anonymized_at IS NOT NULL
            ))
        OR (NEW.object_label IS NULL AND OLD.object_label IS NOT NULL
            AND NOT (OLD.object_kind IN ('user', 'contributor') AND EXISTS (
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

# The same, but that the anonymisation of a copy, by the owner of the journal, forgets any account.
FORGET_ANONYMIZED_OR_COPY = """
CREATE OR REPLACE FUNCTION user_account_forget_anonymized() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    journal_owner name := (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = TG_RELID);
BEGIN
    IF coalesce(current_setting('waterfall.anonymizing_copy', true), '') = 'on'
        AND session_user = journal_owner AND current_user = journal_owner
    THEN
        RETURN NEW;
    END IF;
    IF (NEW.actor_display_name IS NULL AND OLD.actor_display_name IS NOT NULL
            AND NOT EXISTS (
                SELECT FROM user_account
                WHERE id = OLD.actor_user_id AND anonymized_at IS NOT NULL
            ))
        OR (NEW.object_label IS NULL AND OLD.object_label IS NOT NULL
            AND NOT (OLD.object_kind IN ('user', 'contributor') AND EXISTS (
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


def upgrade() -> None:
    """Let the anonymisation of a copy, by the owner of the journal, forget any account."""
    op.execute(FORGET_ANONYMIZED_OR_COPY)


def downgrade() -> None:
    """Write the trigger back as ``0056`` left it."""
    op.execute(FORGET_ANONYMIZED)
