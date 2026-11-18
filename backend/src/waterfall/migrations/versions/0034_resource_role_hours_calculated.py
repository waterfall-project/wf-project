# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours a month of a role, calculated from its headcount and its calendar (EP-10, US-2410).

``resource_role.monthly_hours`` and its constraint are dropped: the headcount of a role is its one
capacity, and its hours a month are calculated as it is read — the headcount times the weekly hours
of its calendar, times 52, divided by 12, to the hundredth (WF-REF-0100). The headcount of each role
is kept as it is, and its hours entered are given up: the capacity of a role may change here
(author's decision of 2026-11-15). The images of the marked revisions (``revision_role``) are not
touched: they keep the hours of their marking.

The descent gives the column back, filled with the hours calculated as the service calculates them —
a half to the even, the division left to the end so that no fraction is cut short —, then required
and never negative again.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "resource_role"
COLUMN = "monthly_hours"
CONSTRAINT = "monthly_hours_not_negative"
# ``scaled`` is the hours a month of a role in hundredths, times 12: its headcount times the weekly
# hours of its calendar times 52 times 100. ``whole`` is its quotient by 12, ``remainder`` what is
# left, 6 at a half; the hundredths rounded, a half to the even, then the hours to the hundredth.
CALCULATED = """
UPDATE resource_role AS r SET monthly_hours = round(
    CASE
        WHEN q.remainder > 6 THEN q.whole + 1
        WHEN q.remainder < 6 THEN q.whole
        ELSE q.whole + mod(q.whole, 2)
    END / 100,
    2
)
FROM (
    SELECT s.id, s.remainder, (s.scaled - s.remainder) / 12 AS whole
    FROM (
        SELECT p.id, p.scaled, mod(p.scaled, 12) AS remainder
        FROM (
            SELECT role.id, role.headcount * (c.monday + c.tuesday + c.wednesday + c.thursday
                + c.friday + c.saturday + c.sunday) * 5200 AS scaled
            FROM resource_role AS role JOIN calendar AS c ON c.id = role.calendar_id
        ) AS p
    ) AS s
) AS q
WHERE q.id = r.id
"""


def upgrade() -> None:
    """Drop the hours entered, and the constraint that kept them positive."""
    op.drop_constraint(op.f(f"ck_{TABLE}_{CONSTRAINT}"), TABLE, type_="check")
    op.drop_column(TABLE, COLUMN)


def downgrade() -> None:
    """Give the column back, filled with the hours calculated, required and never negative."""
    op.add_column(TABLE, sa.Column(COLUMN, sa.Numeric(), nullable=True))
    op.execute(CALCULATED)
    op.alter_column(TABLE, COLUMN, nullable=False)
    op.create_check_constraint(CONSTRAINT, TABLE, f"{COLUMN} >= 0")
