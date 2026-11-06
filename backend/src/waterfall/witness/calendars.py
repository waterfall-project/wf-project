# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars of the witness, and its default one.

``calendars.json``, written by ``create_calendar`` of the resource settings with the identifiers
the witness imposes; the calendar the witness says is the default is created as such, the one the
platform held losing the designation (WF-REF-0120).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import Calendar
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    WeeklyHours,
    calendars_present,
    create_calendar,
)
from waterfall.core.resource_settings.tables import DAYS
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


class Calendars(BaseModel):
    """The calendars of the example ``calendars.json``, as ``listCalendars`` answers them."""

    items: list[Calendar]


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    calendars = witness.read("calendars.json", Calendars).items
    imposed = frozenset(each.calendar_id.root for each in calendars)
    if is_loaded(imposed, calendars_present(session, imposed)):
        return False
    for each in calendars:
        hours = WeeklyHours(*(Decimal(getattr(each.weekly_hours, day).root.root) for day in DAYS))
        create_calendar(
            session,
            CalendarContent(each.label, hours),
            witness.act,
            identifier=each.calendar_id.root,
            default=each.is_default,
        )
    return True
