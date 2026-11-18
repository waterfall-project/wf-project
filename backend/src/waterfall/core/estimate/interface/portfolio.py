# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio reads of the estimate of a revision: its totals by nature and by role (EP-11).

The structure of the costs of the portfolio (WF-PTF-0080) sums, by project, the totals of the
reference budget by cost type, provision lines left out, and those of the remaining to commit,
provisions included; and the labour of each, by role of resources. The estimate of an offer stands
for both. Each amount is rounded once, to the cent, as the indicators round it (EP-11, "Ce que le
cadrage décide").

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class PortfolioTotals:
    """The totals of a revision by cost type, and its labour by role, each an amount.

    ``budget`` leaves the provision lines out; ``remaining`` includes them.
    """

    budget_by_cost_type: Mapping[UUID, Decimal]
    remaining_by_cost_type: Mapping[UUID, Decimal]
    budget_labour_by_role: Mapping[UUID, Decimal]
    remaining_labour_by_role: Mapping[UUID, Decimal]


def portfolio_totals(session: Session, project_id: UUID, revision_id: UUID) -> PortfolioTotals:
    """Give the totals by cost type and the labour by role of a revision of a project."""
    msg = "portfolio_totals is filled by US-2680/L2"
    raise NotImplementedError(msg)
