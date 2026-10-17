# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The name, the first name and the address of an account sort in the order of the code points.

The table of the accounts sorts on them as the contract compares texts, code point by code point,
accents and case included (WF-IHM-0060; sql.md, "Trier et chercher un texte"): the three columns
take the collation ``C``. The index that keeps one address per person, whatever its case, lowered
the address in the collation of its column; in ``C`` it would lower the ASCII letters alone, and
``Élodie@…`` and ``élodie@…`` would be two addresses. It lowers it now in a collation that knows
every letter, the one a search lowers in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "user_account"
COLUMNS = ("last_name", "first_name", "email")
INDEX = "uq_user_account_email_lower"


def _collate(collation: str | None, index: str) -> None:
    op.drop_index(INDEX, table_name=TABLE)
    for name in COLUMNS:
        op.alter_column(
            TABLE,
            name,
            type_=sa.Text(collation=collation),
            existing_type=sa.Text(),
            existing_nullable=False,
        )
    op.create_index(INDEX, TABLE, [sa.text(index)], unique=True)


def upgrade() -> None:
    """Give the three columns the order of the code points; lower the address in every letter."""
    _collate("C", 'lower(email COLLATE "und-x-icu")')


def downgrade() -> None:
    """Give the three columns back the collation of the database, the index with them."""
    _collate(None, "lower(email)")
