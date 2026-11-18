# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value of the reference at a date, private to the module (WF-DEV-0080, US-1520).

The lines of the reference revision outside the provisions, at their budgeted amount, each spread
over the task as the reference dates it — never the current revision's, whose delays leave the
planned value alone —, in proportion to the hours worked on the calendar of the line, as its marking
kept it; a line of a milestone counts whole on its date (``spreading``). The lines and their value
are those the indicators of EP-10 read (``indicator_lines``): one computation, the share of each
line rounded to the cent, whichever reads it (#3566).
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.entries import VALIDATION_FAILED
from waterfall.core.estimate.lining import lines_for_indicators, planned_value_at
from waterfall.core.projects.interface import project_facts
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

REFERENCE_POINTER = "/reference"


def value_of_reference(session: Session, project_id: UUID, reference: UUID, at: date) -> Decimal:
    """Give the planned value of the reference revision at the end of a day, to the cent.

    The reference is the revision designated as such, marked: its lines count at their budgeted
    amount, a line of a provision not at all (WF-REV-0070). Refused 422 on a revision that is not
    the reference the project designates, the current one included: its lines are not the baseline.
    """
    if project_facts(session, project_id).reference_revision_id != reference:
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError(REFERENCE_POINTER, VALIDATION_FAILED),)
        )
    return planned_value_at(lines_for_indicators(session, project_id, reference), at)
