# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The units of duration.

The three constants the days, the weeks and the months convert by, read and written
(WF-PLA-0160): a single row, with a counter of its own, that the bootstrap writes at 8, 40 and 20.
Each is strictly positive. The recalculation of the plannings a change brings is EP-06's: here the
constants are kept, and nothing else moves.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from waterfall.core.resource_settings.tables import SINGLE_ROW, DurationUnit
from waterfall.core.users.interface import Author, read_author
from waterfall.platform.errors import (
    FieldError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
VALIDATION_FAILED = "VALIDATION_FAILED"
DURATION_UNIT_NOT_POSITIVE = "DURATION_UNIT_NOT_POSITIVE"
# The first version of the constants, as the examples of the contract have it.
FIRST_VERSION = 1


@dataclass(frozen=True, slots=True)
class Units:
    """The three constants: the hours of a day and of a week, and the days of a month."""

    hours_per_day: Decimal
    hours_per_week: Decimal
    days_per_month: Decimal


# What the installation starts with (WF-PLA-0160).
DEFAULT_UNITS = Units(Decimal(8), Decimal(40), Decimal(20))


@dataclass(frozen=True, slots=True)
class DurationUnitsView:
    """The constants as they are read, with their audit and their counter."""

    units: Units
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None
    lock_version: int


def _refuse_units(units: Units) -> None:
    """Refuse each constant that is not strictly positive, all named at once (422).

    A zero is ``DURATION_UNIT_NOT_POSITIVE``, as the contract has it; a negative
    one is a value the field refuses.
    """
    faults: list[FieldError] = []
    for name, value in (
        ("hours_per_day", units.hours_per_day),
        ("hours_per_week", units.hours_per_week),
        ("days_per_month", units.days_per_month),
    ):
        if value < 0:
            faults.append(FieldError(f"/{name}", VALIDATION_FAILED))
        elif value == 0:
            faults.append(FieldError(f"/{name}", DURATION_UNIT_NOT_POSITIVE))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def _view(session: Session, row: DurationUnit) -> DurationUnitsView:
    return DurationUnitsView(
        Units(row.hours_per_day, row.hours_per_week, row.days_per_month),
        row.created_at,
        read_author(session, row.created_by),
        row.updated_at,
        read_author(session, row.updated_by),
        row.lock_version,
    )


def get_duration_units(session: Session) -> DurationUnitsView:
    """Read the constants: the installation always holds them, written by the bootstrap."""
    row = session.scalars(
        select(DurationUnit)
        .where(DurationUnit.id == SINGLE_ROW)
        .execution_options(populate_existing=True)
    ).one()
    return _view(session, row)


def install_duration_units(session: Session, act: Act) -> bool:
    """Write the constants at 8, 40 and 20 unless the installation holds them; tell if it wrote."""
    written = session.execute(
        insert(DurationUnit)
        .values(
            id=SINGLE_ROW,
            hours_per_day=DEFAULT_UNITS.hours_per_day,
            hours_per_week=DEFAULT_UNITS.hours_per_week,
            days_per_month=DEFAULT_UNITS.days_per_month,
            lock_version=FIRST_VERSION,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
        .on_conflict_do_nothing()
        .returning(DurationUnit.id)
    ).first()
    return written is not None


def set_duration_units(
    session: Session, units: Units, lock_version: int, act: Act
) -> DurationUnitsView:
    """Write the three constants, if their version is the one read (412), and read them back.

    The constants are refused first (422), the row is locked before its version is judged.
    """
    _refuse_units(units)
    row = session.scalars(
        select(DurationUnit)
        .where(DurationUnit.id == SINGLE_ROW)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if row.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": row.lock_version}
        )
    session.execute(
        update(DurationUnit)
        .where(DurationUnit.id == SINGLE_ROW)
        .values(
            hours_per_day=units.hours_per_day,
            hours_per_week=units.hours_per_week,
            days_per_month=units.days_per_month,
            lock_version=DurationUnit.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    return get_duration_units(session)
