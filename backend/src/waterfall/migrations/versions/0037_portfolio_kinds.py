# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The documents a marking keeps for the portfolio (EP-11, "Tables et migrations"; #3549).

``revision_indicator`` (``0032``) admits five kinds more, each a document of a project the portfolio
sums: ``portfolio_workload``, ``portfolio_cost_structure``, ``portfolio_risks``,
``portfolio_milestones`` and ``portfolio_offer_curves``. No column, no table: the check of the kinds
alone widens, on the table and, by it, on each partition. The trigger that refuses a row whose
``computed_at`` is not the ``marked_at`` of its revision does not change: these documents are
computed at the ``Act`` of the marking, as those of EP-10. The rights of the service are those of
the table. No row is to take up: a revision marked before EP-11 receives nothing (EP-11, "Ce que le
cadrage décide").

The descent gives the check of EP-10 back, and fails while a row of these kinds exists: the check,
validated on every row, refuses it, and nothing is deleted.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "revision_indicator"
# The kinds of EP-10 (``0032``), and those EP-11 adds, all of the scope ``project``.
FORMER_KINDS = (
    "estimate",
    "remaining",
    "project",
    "cost_curve",
    "cost_curve_payment_delays",
    "earned_value_curves",
)
KINDS = (
    *FORMER_KINDS,
    "portfolio_workload",
    "portfolio_cost_structure",
    "portfolio_risks",
    "portfolio_milestones",
    "portfolio_offer_curves",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _known(kinds: tuple[str, ...]) -> None:
    kind = op.f(f"ck_{TABLE}_kind_known")
    op.drop_constraint(kind, TABLE, type_="check")
    op.create_check_constraint(kind, TABLE, _in("kind", kinds))


def upgrade() -> None:
    """Admit the five kinds of the portfolio."""
    _known(KINDS)


def downgrade() -> None:
    """Admit the kinds of EP-10 alone again; refused while a document of the portfolio exists."""
    _known(FORMER_KINDS)
