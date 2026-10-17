# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reports kept copy no personal data of an account of Waterfall (#920).

An entry of ``skipped`` named what the reading left as it was by an address and a code. It now
names an account of Waterfall by its identifier — its name read when the report is consulted, the
neutral label for an account anonymised since — and a person of the provider by her subject, her
names and her address (#918); but a person whose address an account bears (``ALREADY_EXISTS``) by
her subject and that account, the address being the account's. The entries kept before are
rewritten: the last administrator kept, by the account that bears the address; a person whose
address an account bears, kept by the code of this version before it named that account, by her
subject and that account, her names and her address dropped; any other, which named a person or an
account by her address alone — no subject, no name to name her by —, is dropped, as is an entry
whose address no account bears any more, anonymised since. The address an index compares, whatever
its case (``uq_user_account_email_lower``). The ascent thus loses entries too (``sql.md``, rule 5).

No version published bears this table: EP-03, which creates it, is on no installation yet. The code
of this version reads the entries in the form this migration writes alone, with no tolerance of
another: no older code reads them, and no installation keeps an entry of the former form.
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
            CASE
            WHEN former.administrator THEN jsonb_build_object(
                'kind', 'account', 'user_id', account.id, 'code', 'LAST_ADMINISTRATOR'
            )
            WHEN former.copied THEN jsonb_build_object(
                'kind', 'person',
                'subject', each.entry -> 'subject',
                'user_id', account.id,
                'last_name', NULL,
                'first_name', NULL,
                'email', NULL,
                'code', 'ALREADY_EXISTS'
            )
            ELSE each.entry
            END
            ORDER BY each.position
        )
        FROM jsonb_array_elements(report.skipped) WITH ORDINALITY AS each(entry, position)
        CROSS JOIN LATERAL (
            SELECT
                NOT each.entry ? 'kind' AND each.entry ->> 'code' = 'LAST_ADMINISTRATOR'
                    AS administrator,
                each.entry ->> 'kind' = 'person' AND each.entry ->> 'code' = 'ALREADY_EXISTS'
                    AND NOT each.entry ? 'user_id' AS copied
        ) AS former
        LEFT JOIN user_account AS account
            ON (former.administrator OR former.copied)
            AND lower(account.email COLLATE "und-x-icu")
                = lower((each.entry ->> 'email') COLLATE "und-x-icu")
        WHERE account.id IS NOT NULL
            OR (each.entry ? 'kind' AND NOT former.copied)
    ),
    '[]'::jsonb
)
WHERE EXISTS (
    SELECT FROM jsonb_array_elements(report.skipped) AS each(entry)
    WHERE NOT each.entry ? 'kind'
        OR (
            each.entry ->> 'kind' = 'person' AND each.entry ->> 'code' = 'ALREADY_EXISTS'
            AND NOT each.entry ? 'user_id'
        )
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
            ON account.id = (each.entry ->> 'user_id')::uuid
        WHERE coalesce(account.email, each.entry ->> 'email') IS NOT NULL
    ),
    '[]'::jsonb
)
WHERE EXISTS (
    SELECT FROM jsonb_array_elements(report.skipped) AS each(entry) WHERE each.entry ? 'kind'
)
"""


def upgrade() -> None:
    """Rewrite each entry kept in a former form; one that names nothing any more is lost."""
    op.execute(UPGRADE)


def downgrade() -> None:
    """Name again by an address each entry that has one; the others are lost.

    An account by the address it bears, a person by the one the provider held of her — or, whose
    address an account bears, by the address of that account: a person without an address, and an
    account anonymised since, are dropped.
    """
    op.execute(DOWNGRADE)
