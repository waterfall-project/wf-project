# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The timing a schedule of the platform shares: a time, a day of the week, the latest occurrence.

The schedule of the backups (WF-ADM-0170) and the one of the readings of the accounts (WF-ADM-0070)
say when in the same words: every day at a time, or one day of the week at a time, in universal
time, to the minute. Their bounds, the refusals of their fields and the instant a schedule last
announced are one rule, written once.
"""

import re
from datetime import UTC, datetime, time, timedelta

from waterfall.platform.errors import VALIDATION_FAILED, FieldError

VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
WEEKLY = "weekly"
# The days of a weekly schedule, 1 Monday to 7 Sunday (ISO 8601).
WEEKDAYS = (1, 7)
# A time ``HH:MM``, as the contract writes it (`BackupSchedule.at_time`): digits of 0 to 9 alone,
# which ``\d`` would not keep to.
AT_TIME = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")


def parsed_time(text: str) -> time | None:
    """Give the time a text says, ``HH:MM`` in universal time, or ``None`` if it is not one."""
    held = AT_TIME.fullmatch(text)
    return None if held is None else time(int(held[1]), int(held[2]))


def weekday_faults(frequency: str, weekday: int | None) -> list[FieldError]:
    """Ask a day of a weekly schedule, within the week, and refuse one to a daily schedule."""
    if frequency != WEEKLY:
        return [] if weekday is None else [FieldError("/weekday", VALIDATION_FAILED)]
    if weekday is None:
        return [FieldError("/weekday", VALUE_REQUIRED)]
    if weekday < WEEKDAYS[0]:
        return [FieldError("/weekday", VALUE_OUT_OF_RANGE, {"minimum": WEEKDAYS[0]})]
    if weekday > WEEKDAYS[1]:
        return [FieldError("/weekday", VALUE_OUT_OF_RANGE, {"maximum": WEEKDAYS[1]})]
    return []


def latest_occurrence(
    frequency: str, weekday: int | None, at_time: time, now: datetime
) -> datetime:
    """Give the latest moment, ``now`` included, at which a schedule says its task is deposited.

    Daily, the time of the day; weekly, the time of the day of the week (1 Monday to 7 Sunday).
    All in universal time.
    """
    today = now.astimezone(UTC).date()
    day = today
    if frequency == WEEKLY and weekday is not None:
        day = today - timedelta(days=(today.isoweekday() - weekday) % 7)
    occurrence = datetime.combine(day, at_time, tzinfo=UTC)
    if occurrence > now:
        occurrence -= timedelta(days=7 if frequency == WEEKLY else 1)
    return occurrence
