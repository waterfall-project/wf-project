# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The code of a subproject is free, and that of a project may bear a slash (US-3270, #3966).

The schema of the reprise of the codes, before its data (0047), as the conception of EP-33 says it
("Tables et migrations"): the code of a subproject passes to 100 characters, and loses the check
of the characters a tab refuses (``code_form``); ``cost_line.subproject_code``, the code of the
subproject a line is imputed to, takes the same bound; the code of a project loses the check that
refused a slash (``code_without_slash``). 100, because the reprise writes the code of a project of
50 characters, a slash, then a former code of 31: 82. The reserved names were the service's alone.

Every constraint is relaxed: the code before runs on it as it did, and every row holds. The checks
are dropped and created again, validated at once, not ``NOT VALID`` then validated apart, as
``docs/dev/sql.md`` (rule 6) asks of a long lock, and this is tolerable: dropping the check of
``cost_line`` takes its exclusive lock, which the transaction of the migrations, one for the whole
upgrade, holds until its end whatever follows, so a validation apart would shorten no lock; and
the reprise of 0047, in that same transaction, rewrites every line imputed and deletes those that
wait, reading the whole table anyway — the scan of the check, under the lock already held, adds a
read of the table to it. A validation in a transaction of its own would split the upgrade, which
then could stop between the schema and the reprise. ``subproject`` is small.

The descent creates the former checks again: it fails while a code holds what they refuse — a
subproject code beyond 31 characters or bearing a character a tab refuses, a line of cost whose
code is beyond 50, a project code bearing a slash —, which 0047 writes and the descent of 0047 does
not always undo; the schema then stays.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FORMER_SUBPROJECT_LENGTH = 31
SUBPROJECT_LENGTH = 100
FORMER_COST_LINE_LENGTH = 50
# The characters the name of a tab of a workbook refuses, as a class of a regular expression of
# PostgreSQL, as 0020 wrote it.
TAB_FORBIDDEN = r"[:\\/?*\[\]]"


def _bound_subproject_code(longest: int) -> None:
    op.drop_constraint(op.f("ck_subproject_code_length"), "subproject", type_="check")
    op.create_check_constraint(
        "code_length", "subproject", f"char_length(code) BETWEEN 1 AND {longest}"
    )


def _bound_cost_line_code(longest: int) -> None:
    op.drop_constraint(op.f("ck_cost_line_subproject_code_length"), "cost_line", type_="check")
    op.create_check_constraint(
        "subproject_code_length", "cost_line", f"char_length(subproject_code) <= {longest}"
    )


def upgrade() -> None:
    """Free the code of a subproject to 100 characters, and the code of a project of its slash."""
    _bound_subproject_code(SUBPROJECT_LENGTH)
    op.drop_constraint(op.f("ck_subproject_code_form"), "subproject", type_="check")
    _bound_cost_line_code(SUBPROJECT_LENGTH)
    op.drop_constraint(op.f("ck_project_code_without_slash"), "project", type_="check")


def downgrade() -> None:
    """Bound the codes again as 0020 and 0027 did; fails while a code holds what they refuse."""
    op.create_check_constraint("code_without_slash", "project", "code !~ '/'")
    _bound_cost_line_code(FORMER_COST_LINE_LENGTH)
    op.create_check_constraint("code_form", "subproject", f"code !~ '{TAB_FORBIDDEN}'")
    _bound_subproject_code(FORMER_SUBPROJECT_LENGTH)
