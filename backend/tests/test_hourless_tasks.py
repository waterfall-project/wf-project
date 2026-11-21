# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Which tasks ``hourless_tasks`` refuses, on the calendars it is given (US-3060/L3, #4250).

The judgement is a function of the weeks of the calendars and of the roles each task bears: the
weeks are given in place of the database's, and a task is named or not by their intersection.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest

from waterfall.core.estimate.costing import hourless_tasks

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy.orm import Session

ROLE = UUID(int=1)
OTHER = UUID(int=2)
UNKNOWN = UUID(int=3)
WEEKDAYS_CALENDAR = UUID(int=11)
WEEKENDS_CALENDAR = UUID(int=12)
WEEKDAYS = (Decimal(8),) * 5 + (Decimal(0),) * 2
WEEKENDS = (Decimal(0),) * 5 + (Decimal(8),) * 2
SESSION = cast("Session", None)


def _given(monkeypatch: pytest.MonkeyPatch) -> None:
    weeks = {WEEKDAYS_CALENDAR: WEEKDAYS, WEEKENDS_CALENDAR: WEEKENDS}

    def hours(_session: Session, ids: Collection[UUID]) -> dict[UUID, tuple[Decimal, ...]]:
        return {each: weeks[each] for each in set(ids)}

    def roles(*_asked: object, **_kept: object) -> list[object]:
        return []

    monkeypatch.setattr("waterfall.core.estimate.costing.calendar_hours", hours)
    monkeypatch.setattr("waterfall.core.estimate.costing.read_roles", roles)


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_none_of_whose_roles_has_a_calendar_is_not_refused_for_want_of_an_hour() -> None:
    # « [L]e calendrier par défaut s'applique aux tâches qui ne portent aucune ligne de
    # main-d'œuvre » : sans calendrier de rôle à recouper, il n'y a pas de semaine sans heure.
    assert list(hourless_tasks(SESSION, {"task": {ROLE, OTHER}}, {})) == []


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_whose_roles_calendars_share_no_hour_is_still_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _given(monkeypatch)
    roles: dict[str, set[UUID]] = {"hourless": {ROLE, OTHER}, "worked": {ROLE}, "none": set()}
    calendars = {ROLE: WEEKDAYS_CALENDAR, OTHER: WEEKENDS_CALENDAR}
    assert list(hourless_tasks(SESSION, roles, calendars)) == [("hourless", [])]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_role_without_a_calendar_does_not_hide_the_hourless_week_of_the_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _given(monkeypatch)
    held = {"task": {ROLE, OTHER, UNKNOWN}}
    calendars = {ROLE: WEEKDAYS_CALENDAR, OTHER: WEEKENDS_CALENDAR}
    assert [task for task, _ in hourless_tasks(SESSION, held, calendars)] == ["task"]
