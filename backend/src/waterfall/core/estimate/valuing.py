# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value of the reference at a date, private to the module (WF-DEV-0080, US-1520).

The lines of the reference revision outside the provisions, at their budgeted amount, each spread
over the task as the reference dates it — never the current revision's, whose delays leave the
planned value alone —, in proportion to the hours worked on the calendar of the line; a line of a
milestone counts whole on its date (``spreading``). EP-10 reads it for its curves and its indexes.
"""

from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.entries import PROVISION, VALIDATION_FAILED
from waterfall.core.estimate.placing import placed_lines, placement_of, role_weeks
from waterfall.core.estimate.reading import budgeted_of
from waterfall.core.estimate.spreading import PlannedLine
from waterfall.core.estimate.spreading import planned_value as value_of
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
    placed = placed_lines(session, project_id, reference)
    natures = category_labels(session, {each.line.cost_category_id for each in placed})
    weeks = role_weeks(
        session, {each.line.resource_role_id for each in placed if each.line.resource_role_id}
    )
    lines = [
        PlannedLine(budgeted_of(each.line), placement_of(each, weeks))
        for each in placed
        if (nature := natures.get(each.line.cost_category_id)) is None
        or nature.cost_type_kind != PROVISION
    ]
    return value_of(lines, at)
