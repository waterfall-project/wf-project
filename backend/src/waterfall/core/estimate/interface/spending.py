# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spending projection of an estimate, by nature of cost and by month (US-2050).

``project_spending`` spreads the amount of each line of a revision outside the provisions over the
hours worked of its task, the parts of a line rounded to the cent so that they sum to its amount
(``getProjectSpending``, WF-DEV-0100): on the budgeted amounts of the reference, or on the
remaining to commit of a marked revision or of the current one, from the date of calculation; on
request each part is shifted by the payment delay of its line. A marked revision is computed when
read. It writes nothing.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.disbursing import amount_parts
from waterfall.core.estimate.spending import (
    SpendingAsked,
    SpendingCategory,
    SpendingCostType,
    SpendingView,
    read_spending,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

# The types are the interface's own to give: only a name in ``__all__`` is re-exported.
__all__ = [
    "SpendingAsked",
    "SpendingCategory",
    "SpendingCostType",
    "SpendingView",
    "amount_parts",
    "project_spending",
]


def project_spending(session: Session, project_id: UUID, asked: SpendingAsked) -> SpendingView:
    """Give the projection of spending of a project on a basis, by nature, category and month.

    Refused 409 on the basis of the reference, or of the current revision, a project lacks; 422 on
    a revision that is not a marked one of the project, on a subproject the project does not have,
    and on a labour category without an hourly rate for the reference year of the revision read.
    """
    return read_spending(session, project_id, asked)
