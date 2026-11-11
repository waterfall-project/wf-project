# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of an estimate and the planned value of its reference (US-1520).

``workload`` spreads the hours of the labour lines of a revision over the working hours of their
tasks, by role and by month, through the subpackage ``spreading``, and sets the capacity of each
role beside them (``getProjectWorkload``, WF-DEV-0070): on the budgeted load of the reference, or
on the remaining to commit of a marked revision or of the current one. ``planned_value`` gives the
planned value of the reference at a date, from the lines of the reference revision outside the
provisions (WF-DEV-0080): no operation of the contract serves it before EP-10, which reads it.
Neither writes anything.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.valuing import value_of_reference
from waterfall.core.estimate.workloading import read_workload

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.workloading import WorkloadAsked, WorkloadView


def workload(session: Session, project_id: UUID, asked: WorkloadAsked) -> WorkloadView:
    """Give the plan of workload of a project on a basis, by role and by month.

    Refused 409 on the basis of the reference, or of the current revision, a project lacks; 422 on
    a revision that is not a marked one of the project, and on a node the reference does not hold.
    """
    return read_workload(session, project_id, asked)


def planned_value(session: Session, project_id: UUID, reference: UUID, at: date) -> Decimal:
    """Give the planned value of the reference revision at the end of a day, to the cent.

    The lines of the reference outside the provisions, at their budgeted amount, spread over their
    tasks as the reference dates them; a line of a milestone counts whole on its date. Refused 422
    on a revision that is not the reference the project designates.
    """
    return value_of_reference(session, project_id, reference, at)
