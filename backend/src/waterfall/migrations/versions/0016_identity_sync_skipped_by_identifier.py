# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reports kept name an account of Waterfall by its identifier alone (#920).

An entry of ``skipped`` named what the reading left as it was by an address and a code. It now
names an account of Waterfall by its identifier — its name read when the report is consulted, the
neutral label for an account anonymised since — and a person of the provider by her subject, her
names and her address (#918). The entries kept before are rewritten: the last administrator kept,
by the account that bears the address; any other, which named a person or an account by her
address alone — no subject, no name to name her by —, is dropped, as is a last administrator whose
address no account bears any more, anonymised since. The address an index compares, whatever its
case (``uq_user_account_email_lower``).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = """
UPDATE identity_sync_report AS report
SET skipped = coalesce(
    (
        SELECT jsonb_agg(
            CASE WHEN each.entry ? 'kind' THEN each.entry
            ELSE jsonb_build_object(
                'kind', 'account', 'user_id', account.id, 'code', 'LAST_ADMINISTRATOR'
            )
            END
            ORDER BY each.position
        )
        FROM jsonb_array_elements(report.skipped) WITH ORDINALITY AS each(entry, position)
        LEFT JOIN user_account AS account
            ON NOT each.entry ? 'kind'
            AND each.entry ->> 'code' = 'LAST_ADMINISTRATOR'
            AND lower(account.email COLLATE "und-x-icu")
                = lower((each.entry ->> 'email') COLLATE "und-x-icu")
        WHERE each.entry ? 'kind' OR account.id IS NOT NULL
    ),
    '[]'::jsonb
)
WHERE EXISTS (
    SELECT FROM jsonb_array_elements(report.skipped) AS each(entry) WHERE NOT each.entry ? 'kind'
)
"""

DOWNGRADE = """
UPDATE identity_sync_report AS report
SET skipped = coalesce(
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'email', coalesce(account.email, each.entry ->> 'email'),
                'code', each.entry ->> 'code'
            )
            ORDER BY each.position
        )
        FROM jsonb_array_elements(report.skipped) WITH ORDINALITY AS each(entry, position)
        LEFT JOIN user_account AS account
            ON each.entry ->> 'kind' = 'account'
            AND account.id = (each.entry ->> 'user_id')::uuid
        WHERE coalesce(account.email, each.entry ->> 'email') IS NOT NULL
    ),
    '[]'::jsonb
)
WHERE EXISTS (
    SELECT FROM jsonb_array_elements(report.skipped) AS each(entry) WHERE each.entry ? 'kind'
)
"""


def upgrade() -> None:
    """Rewrite each entry kept in the former form."""
    op.execute(UPGRADE)


def downgrade() -> None:
    """Name again by an address each entry that has one; the others are lost.

    An account by the address it bears, a person by the one the provider held of her: a person
    without an address, and an account anonymised since, are dropped.
    """
    op.execute(DOWNGRADE)
