# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rule of the durations of an import of MS Project in calendar gap (EP-24, US-2000).

``import_report`` receives ``duration_rule``: how a planning of MS Project whose constants or
calendars differ from those of the installation converts its durations — ``keep_durations``, the
default, or ``keep_dates`` (WF-INTF-0040, WF-PLA-0160) —, null for any other import. It is born
null, and no row is to take up: an import analysed before it is read as without a gap. The report
stays the JSON of ``report``; the service changes the row already, and no right is granted.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "import_report"


def upgrade() -> None:
    """Add the rule of the durations of an import, null, and its two constraints."""
    op.add_column(TABLE, sa.Column("duration_rule", sa.Text(), nullable=True))
    op.create_check_constraint(
        "duration_rule_known", TABLE, "duration_rule IN ('keep_durations', 'keep_dates')"
    )
    op.create_check_constraint(
        "duration_rule_of_a_planning",
        TABLE,
        "duration_rule IS NULL OR kind = 'ms_project_schedule'",
    )


def downgrade() -> None:
    """Drop the rule of the durations of an import, its constraints with it."""
    op.drop_constraint(op.f("ck_import_report_duration_rule_of_a_planning"), TABLE, type_="check")
    op.drop_constraint(op.f("ck_import_report_duration_rule_known"), TABLE, type_="check")
    op.drop_column(TABLE, "duration_rule")
