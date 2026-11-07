# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars and the units of duration (US-0860: WF-REF-0110, 0120, WF-PLA-0160).

Every answer passes through ``ContractClient``, which checks it against the contract. The
calendars are read and written as a manager does (the permissions to read and to change the
resource settings), or as a reader and as a session of no permission of the reference.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select, update
from support import WITNESS

from waterfall.core.resource_settings import interface
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    CalendarFilters,
    CalendarSort,
    CalendarWindow,
    WeeklyHours,
    create_calendar,
    get_duration_units,
    install_duration_units,
    list_calendars,
    read_calendar,
    set_default_calendar,
)
from waterfall.core.resource_settings.interface import calendars as calendars_module
from waterfall.core.resource_settings.tables import Calendar
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.settings import WitnessSettings
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
UNITS = "/api/v1/reference/duration-units"
PLATFORM = Act(None, utc_now())
STANDARD = ("8", "8", "8", "8", "8", "0", "0")
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
FOUR_DAYS = ("10", "10", "10", "10", "0", "0", "0")


def week(*hours: str) -> dict[str, str]:
    """Name the hours of a week by day: five days of eight hours unless said otherwise."""
    return dict(zip(DAYS, hours or STANDARD, strict=True))


def hours_of(*hours: str) -> WeeklyHours:
    """Give the hours of a week as the module takes them."""
    return WeeklyHours(*(Decimal(each) for each in hours or STANDARD))


@pytest.fixture
def sessions(reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the resource settings: of none, of reading, of changing."""
    return reference_sessions("resource_settings")


def seed(
    database: Database,
    label: str,
    *hours: str,
    default: bool = False,
    identifier: UUID | None = None,
) -> UUID:
    """Create a calendar around the service, by the module; give its identifier."""
    with database.transaction() as session:
        created = create_calendar(
            session,
            CalendarContent(label, hours_of(*hours)),
            PLATFORM,
            identifier=identifier,
            default=default,
        )
    return created.calendar_id


def deactivate(database: Database, calendar_id: UUID) -> None:
    """Deactivate a calendar around the service, as the owner of the data would."""
    with database.transaction() as session:
        session.get_one(Calendar, calendar_id).is_active = False


def post(api: ContractClient, headers: dict[str, str], label: str, *hours: str) -> dict[str, Any]:
    """Create a calendar by the service; give its answer."""
    sent = {"label": label, "weekly_hours": week(*hours)}
    response = api.post(CALENDARS, headers=headers, json=sent)
    assert response.status_code == 201
    return response.json()


def listing(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the calendars by the service; give the answer."""
    response = api.get(f"{CALENDARS}?{query}", headers=headers)
    assert response.status_code == 200
    return response.json()


def labels(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the labels of the calendars a query keeps, in their order."""
    return [each["label"] for each in listing(api, headers, query)["items"]]


def refusal(response: Any) -> tuple[int, str, dict[str, Any], list[dict[str, Any]]]:
    """Give the status, the code, the parameters and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {}), body.get("fields", [])


def put(api: ContractClient, headers: dict[str, str], path: str, **sent: Any) -> Any:
    """Send a PUT with the body given."""
    return api.put(f"{CALENDARS}/{path}", headers=headers, json=sent)


def constants(body: dict[str, Any]) -> list[str]:
    """Give the three constants of an answer."""
    return [body[name] for name in ("hours_per_day", "hours_per_week", "days_per_month")]


@pytest.mark.requirement("WF-REF-0110-A")
def test_a_calendar_is_entered_by_a_label_and_seven_values_of_hours(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « Un calendrier se saisit par un libellé et sept valeurs d'heures, du lundi au dimanche, et
    # aucune autre donnée n'est demandée » : created active, not the default, its commands those
    # of the example of the contract.
    created = post(api, sessions.changing, "Semaine de trente-cinq heures", *("7",) * 5, "0", "0")
    assert created["weekly_hours"] == week("7", "7", "7", "7", "7", "0", "0")
    assert (created["is_default"], created["is_active"]) == (False, True)
    assert created["lock_version"] == 1
    assert created["available_commands"] == [
        {"command": "deactivate", "is_available": True, "missing_conditions": []},
        {"command": "set_default", "is_available": True, "missing_conditions": []},
    ]
    read = listing(api, sessions.changing)["items"]
    assert [each["calendar_id"] for each in read] == [created["calendar_id"]]


@pytest.mark.requirement("WF-REF-0110-A")
def test_a_calendar_asks_for_nothing_but_its_label_and_its_week(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « …aucune autre donnée n'est demandée » : a week lacking a day is refused, the label too.
    short = {"label": "Court", "weekly_hours": {"monday": "8"}}
    lacking = api.post(CALENDARS, headers=sessions.changing, json=short)
    assert refusal(lacking)[:2] == (422, "VALIDATION_FAILED")
    assert {fault["pointer"] for fault in refusal(lacking)[3]} == {
        f"/weekly_hours/{day}" for day in DAYS[1:]
    }
    blank = {"label": " ", "weekly_hours": week()}
    refused = api.post(CALENDARS, headers=sessions.changing, json=blank)
    assert refusal(refused)[:2] == (422, "VALIDATION_FAILED")
    assert listing(api, sessions.changing)["items"] == []
    # The contract (CalendarWrite) does not close the body: a field beyond the two is ignored,
    # the calendar is created active and not the default whatever was sent.
    extra = {"label": "En trop", "weekly_hours": week(), "is_default": True, "is_active": False}
    accepted = api.post(CALENDARS, headers=sessions.changing, json=extra)
    assert accepted.status_code == 201
    assert (accepted.json()["is_default"], accepted.json()["is_active"]) == (False, True)


@pytest.mark.requirement("WF-REF-0110-A")
@pytest.mark.parametrize("update", [False, True])
def test_the_hours_of_a_day_outside_zero_to_twenty_four_are_refused_day_by_day(
    api: ContractClient, database: Database, sessions: PartSessions, update: bool
) -> None:
    # Hours of a day from 0 to 24, on creation as on change: each day named with the bound it
    # crosses, nothing written. A third decimal is no hour the column keeps.
    kept = seed(database, "Gardé")
    sent = {"label": "Refusé", "weekly_hours": week("25", "8", "8", "8", "8", "-7", "0.001")}
    response = (
        api.patch(
            f"{CALENDARS}/{kept}", headers=sessions.changing, json={**sent, "lock_version": 1}
        )
        if update
        else api.post(CALENDARS, headers=sessions.changing, json=sent)
    )
    status, code, _, fields = refusal(response)
    assert (status, code) == (422, "VALIDATION_FAILED")
    assert fields == [
        {
            "pointer": "/weekly_hours/monday",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"maximum": "24"},
        },
        {
            "pointer": "/weekly_hours/saturday",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": "0"},
        },
        {"pointer": "/weekly_hours/sunday", "code": "VALIDATION_FAILED"},
    ]
    assert labels(api, sessions.changing) == ["Gardé"]


@pytest.mark.requirement("WF-REF-0110-A")
def test_the_bounds_of_the_hours_of_a_day_are_themselves_admitted(
    api: ContractClient, sessions: PartSessions
) -> None:
    created = post(
        api, sessions.changing, "Limites", "0", "24", "7.5", "7.25", "0.00", "10.50", "24.00"
    )
    assert created["weekly_hours"] == week("0", "24", "7.5", "7.25", "0", "10.5", "24")


@pytest.mark.requirement("WF-REF-0110-A")
def test_two_calendars_of_the_same_label_are_refused_deactivated_ones_included(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # « …deux calendriers de même libellé sont refusés. » : on creation and on change, the one that
    # holds the label named; a calendar keeps its own label when it is changed.
    held = seed(database, "Semaine de trente-neuf heures")
    deactivate(database, held)
    other = seed(database, "Semaine de quatre jours", *FOUR_DAYS)
    taken = {"label": "Semaine de trente-neuf heures", "weekly_hours": week()}
    created = api.post(CALENDARS, headers=sessions.changing, json=taken)
    expected = [
        {
            "pointer": "/label",
            "code": "ALREADY_EXISTS",
            "params": {"conflicting_object_id": str(held)},
        }
    ]
    assert refusal(created)[:2] == (409, "ALREADY_EXISTS")
    assert refusal(created)[3] == expected
    changed = api.patch(
        f"{CALENDARS}/{other}", headers=sessions.changing, json={**taken, "lock_version": 1}
    )
    assert refusal(changed)[:2] == (409, "ALREADY_EXISTS")
    assert refusal(changed)[3] == expected
    own = {
        "label": "Semaine de quatre jours",
        "weekly_hours": week("9", "9", "9", "9", "0", "0", "0"),
    }
    renamed = api.patch(
        f"{CALENDARS}/{other}", headers=sessions.changing, json={**own, "lock_version": 1}
    )
    assert renamed.status_code == 200
    assert renamed.json()["lock_version"] == 2
    assert renamed.json()["weekly_hours"] == own["weekly_hours"]


@pytest.mark.requirement("WF-REF-0110-A")
def test_a_change_is_refused_when_its_version_is_stale_or_its_calendar_unknown(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    kept = seed(database, "Gardé")
    sent = {"label": "Autre", "weekly_hours": week(), "lock_version": 7}
    stale = api.patch(f"{CALENDARS}/{kept}", headers=sessions.changing, json=sent)
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    unknown = api.patch(f"{CALENDARS}/{uuid4()}", headers=sessions.changing, json=sent)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    assert labels(api, sessions.changing) == ["Gardé"]


@pytest.mark.requirement("WF-REF-0120-A")
def test_designating_a_calendar_the_default_takes_the_designation_from_the_previous_one(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # « Désigner un calendrier par défaut retire cette désignation au précédent. » : the version of
    # the previous one advances, and its commands are those of a calendar that is not the default.
    standard = seed(database, "Semaine standard", default=True)
    four_days = seed(database, "Semaine de quatre jours", *FOUR_DAYS)
    response = put(api, sessions.changing, f"{four_days}/default", lock_version=1)
    assert response.status_code == 200
    designated = response.json()
    assert (designated["is_default"], designated["lock_version"]) == (True, 2)
    assert designated["available_commands"] == [
        {
            "command": "deactivate",
            "is_available": False,
            "missing_conditions": ["calendar_not_default"],
        }
    ]
    by_id = {each["calendar_id"]: each for each in listing(api, sessions.changing)["items"]}
    previous = by_id[str(standard)]
    assert (previous["is_default"], previous["lock_version"]) == (False, 2)
    assert [each["is_default"] for each in by_id.values()].count(True) == 1
    assert previous["available_commands"][0] == {
        "command": "deactivate",
        "is_available": True,
        "missing_conditions": [],
    }


@pytest.mark.requirement("WF-REF-0120-A")
def test_a_deactivated_calendar_is_not_designated_and_the_default_one_answers_as_it_is(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    standard = seed(database, "Semaine standard", default=True)
    thirty_nine = seed(database, "Semaine de trente-neuf heures")
    deactivate(database, thirty_nine)
    inactive = put(api, sessions.changing, f"{thirty_nine}/default", lock_version=1)
    assert refusal(inactive)[:3] == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "calendar_active"},
    )
    # The default one: 200, nothing changed, the version judged first.
    again = put(api, sessions.changing, f"{standard}/default", lock_version=1)
    assert again.status_code == 200
    assert (again.json()["is_default"], again.json()["lock_version"]) == (True, 1)
    stale = put(api, sessions.changing, f"{standard}/default", lock_version=4)
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    unknown = put(api, sessions.changing, f"{uuid4()}/default", lock_version=1)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-REF-0120-A")
def test_the_default_calendar_is_not_deactivated_until_another_is_designated(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # « La désactivation du calendrier par défaut est refusée tant qu'un autre n'a pas été
    # désigné. » : refused, the calendar unchanged; once another is the default, it goes, and
    # comes back.
    standard = seed(database, "Semaine standard", default=True)
    four_days = seed(database, "Semaine de quatre jours", *FOUR_DAYS)
    refused = put(api, sessions.changing, f"{standard}/activation", is_active=False, lock_version=1)
    assert refusal(refused)[:3] == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "calendar_not_default"},
    )
    put(api, sessions.changing, f"{four_days}/default", lock_version=1)
    off = put(api, sessions.changing, f"{standard}/activation", is_active=False, lock_version=2)
    assert off.status_code == 200
    assert (off.json()["is_active"], off.json()["lock_version"]) == (False, 3)
    assert off.json()["available_commands"] == [
        {"command": "reactivate", "is_available": True, "missing_conditions": []},
        {
            "command": "set_default",
            "is_available": False,
            "missing_conditions": ["calendar_active"],
        },
    ]
    on = put(api, sessions.changing, f"{standard}/activation", is_active=True, lock_version=3)
    assert (on.json()["is_active"], on.json()["lock_version"]) == (True, 4)
    stale = put(api, sessions.changing, f"{standard}/activation", is_active=False, lock_version=3)
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 4})
    again = put(api, sessions.changing, f"{standard}/activation", is_active=True, lock_version=4)
    assert (again.json()["is_active"], again.json()["lock_version"]) == (True, 4)
    unknown = put(api, sessions.changing, f"{uuid4()}/activation", is_active=True, lock_version=1)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-REF-0120-A")
def test_the_database_keeps_a_single_default_under_concurrent_designations(
    database: Database,
) -> None:
    # Two transactions designate two calendars at once, each from the version it read: the lock of
    # the designation lines them up, the later one retires the earlier, and the unique partial
    # index never refuses either.
    seed(database, "A", default=True)
    for round_ in range(5):
        first, second = seed(database, f"B{round_}"), seed(database, f"C{round_}")
        barrier = Barrier(2)

        def designate(calendar_id: UUID, barrier: Barrier = barrier) -> None:
            with database.transaction() as session:
                version = read_calendar(session, calendar_id).lock_version
                barrier.wait(timeout=10)
                set_default_calendar(session, calendar_id, version, PLATFORM)

        with ThreadPoolExecutor(max_workers=2) as pool:
            for outcome in [pool.submit(designate, first), pool.submit(designate, second)]:
                outcome.result(timeout=30)
        with database.transaction() as session:
            held = select(Calendar.id).where(Calendar.is_default.is_(True))
            defaults = session.scalars(held).all()
        assert len(defaults) == 1


@pytest.mark.requirement("WF-REF-0120-A")
def test_a_calendar_created_as_the_default_retires_the_one_the_platform_held(
    database: Database,
) -> None:
    held = seed(database, "Installé", default=True)
    chosen = seed(database, "Choisi", default=True)
    with database.transaction() as session:
        before, after = read_calendar(session, held), read_calendar(session, chosen)
    assert (before.is_default, before.lock_version) == (False, 2)
    assert (after.is_default, after.lock_version) == (True, 1)


@pytest.mark.requirement("WF-REF-0110-A")
def test_a_change_that_would_leave_a_task_without_an_hour_is_refused_and_writes_nothing(
    api: ContractClient,
    database: Database,
    sessions: PartSessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The question is EP-06's (WF-PLA-0010); the interface asks it before writing, for a change of
    # hours and for a designation.
    standard = seed(database, "Semaine standard", default=True)
    other = seed(database, "Autre")

    def never(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(calendars_module, "calendar_change_is_admissible", never)
    sent = {"label": "Semaine standard", "weekly_hours": week("0", "0", "0", "0", "0", "0", "0")}
    changed = api.patch(
        f"{CALENDARS}/{standard}", headers=sessions.changing, json={**sent, "lock_version": 1}
    )
    assert refusal(changed)[:3] == (
        422,
        "TASK_WITHOUT_WORKING_HOURS",
        {"resource_roles": [], "projects": []},
    )
    designated = put(api, sessions.changing, f"{other}/default", lock_version=1)
    assert refusal(designated)[1] == "TASK_WITHOUT_WORKING_HOURS"
    with database.transaction() as session:
        assert read_calendar(session, standard).weekly_hours == hours_of()
        assert read_calendar(session, standard).is_default
        assert not read_calendar(session, other).is_default


def test_the_question_of_the_tasks_a_calendar_change_would_leave_idle_is_always_answered_yes(
    database: Database,
) -> None:
    calendar_id = seed(database, "Semaine standard")
    with database.transaction() as session:
        admissible = interface.calendar_change_is_admissible(
            session, calendar_id, hours_of("0", "0", "0", "0", "0", "0", "0"), default=True
        )
    assert admissible


@pytest.mark.requirement("WF-REF-0110-A")
def test_the_active_calendars_are_read_by_any_session_and_their_commands_by_who_may_change(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    seed(database, "Semaine standard", default=True)
    seed(database, "Semaine de quatre jours", *FOUR_DAYS)
    seen = [listing(api, headers)["items"] for headers in (sessions.without, sessions.reading)]
    assert all(each["available_commands"] == [] for items in seen for each in items)
    assert [each["label"] for each in seen[0]] == ["Semaine de quatre jours", "Semaine standard"]
    managed = listing(api, sessions.changing)["items"]
    assert [len(each["available_commands"]) for each in managed] == [2, 1]


@pytest.mark.requirement("WF-REF-0150-A")
@pytest.mark.parametrize(
    ("query", "kept"),
    [("include_inactive=true", ["Actif", "Désactivé"]), ("is_active=false", ["Désactivé"])],
)
def test_the_deactivated_calendars_ask_for_the_permission_to_change_the_resource_settings(
    api: ContractClient,
    database: Database,
    sessions: PartSessions,
    query: str,
    kept: list[str],
) -> None:
    # The `*_inactive_forbidden` example of the contract: 403, the permission to change named —
    # the permission to read the part does not open the deactivated calendars (#2084).
    seed(database, "Actif", default=True)
    deactivate(database, seed(database, "Désactivé"))
    for headers in (sessions.without, sessions.reading):
        response = api.get(f"{CALENDARS}?{query}", headers=headers)
        assert refusal(response)[:3] == (
            403,
            "PERMISSION_MISSING",
            {"missing_permission": "resource_settings.write"},
        )
    assert labels(api, sessions.changing, query) == kept
    assert labels(api, sessions.changing) == ["Actif"]


@pytest.mark.requirement("WF-REF-0110-A")
def test_the_list_is_searched_on_the_label_and_filtered_on_the_state(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    seed(database, "Semaine standard", default=True)
    seed(database, "Équipe de nuit", "0", "0", "0", "0", "0", "8", "8")
    deactivate(database, seed(database, "Semaine de quatre jours", *FOUR_DAYS))
    # Case and accents are ignored; the hours are not searched.
    assert labels(api, sessions.changing, "search=EQUIPE") == ["Équipe de nuit"]
    assert labels(api, sessions.changing, "search=8") == []
    assert labels(api, sessions.changing, "search=semaine&include_inactive=true") == [
        "Semaine de quatre jours",
        "Semaine standard",
    ]
    assert labels(api, sessions.changing, "is_active=true&include_inactive=true") == [
        "Semaine standard",
        "Équipe de nuit",
    ]
    assert labels(api, sessions.changing, "is_active=false") == ["Semaine de quatre jours"]


@pytest.mark.requirement("WF-REF-0110-A")
@pytest.mark.parametrize(
    ("column", "orders"),
    [
        ("label", ("ABCD", "DCBA")),
        ("monday", ("ABCD", "ABCD")),
        ("sunday", ("ABCD", "DABC")),
        ("friday", ("ABCD", "ABCD")),
        ("weekly_hours", ("BACD", "DACB")),
        ("is_default", ("DABC", "ABCD")),
        ("is_active", ("ABDC", "CABD")),
    ],
)
def test_every_column_of_the_list_sorts_equals_by_label_in_either_direction(
    api: ContractClient,
    database: Database,
    sessions: PartSessions,
    column: str,
    orders: tuple[str, str],
) -> None:
    # A: 8 h on the weekdays; B: 8 h on Monday and Friday; C: as A, deactivated; D: the default,
    # as A with 8 h on Sunday. Equals come by label, ascending whatever the direction.
    seed(database, "A", "8", "8", "8", "8", "8", "0", "0")
    seed(database, "B", "8", "0", "0", "0", "8", "0", "0")
    deactivate(database, seed(database, "C", "8", "8", "8", "8", "8", "0", "0"))
    seed(database, "D", "8", "8", "8", "8", "8", "0", "8", default=True)
    query = f"sort_by={column}&include_inactive=true"
    ascending, descending = orders
    assert "".join(labels(api, sessions.changing, query)) == ascending
    assert "".join(labels(api, sessions.changing, f"{query}&sort_order=desc")) == descending


@pytest.mark.requirement("WF-REF-0110-A")
def test_the_sum_of_the_week_sorts_and_the_pages_cut_the_order(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    seed(database, "A", "8", "8", "8", "8", "8", "0", "0")
    seed(database, "B", "4", "0", "0", "0", "0", "0", "2")
    seed(database, "C", "10", "10", "10", "10", "0", "0", "0")
    seed(database, "D", "1", "1", "1", "1", "1", "1", "1", default=True)
    assert labels(api, sessions.changing, "sort_by=weekly_hours") == ["B", "D", "A", "C"]
    assert labels(api, sessions.changing, "sort_by=monday&sort_order=desc") == ["C", "A", "B", "D"]
    page = listing(api, sessions.changing, "limit=2&offset=1")
    assert [each["label"] for each in page["items"]] == ["B", "C"]
    assert page["meta"] == {"limit": 2, "offset": 1, "total": 4}
    refused = api.get(f"{CALENDARS}?sort_by=color", headers=sessions.changing)
    assert refusal(refused)[:2] == (422, "VALIDATION_FAILED")


@pytest.mark.requirement("WF-PLA-0160-A")
def test_the_constants_are_read_by_any_session_at_eight_forty_and_twenty(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # « …8, 40 et 20 à l'installation » : the bootstrap writes them; a second writing finds them.
    with database.transaction() as session:
        assert install_duration_units(session, PLATFORM)
    with database.transaction() as session:
        assert not install_duration_units(session, PLATFORM)
        assert get_duration_units(session).lock_version == 1
    for headers in (sessions.without, sessions.changing):
        response = api.get(UNITS, headers=headers)
        assert response.status_code == 200
        assert constants(response.json()) == ["8", "40", "20"]
        assert response.json()["lock_version"] == 1
        assert response.json()["audit"]["created_by"] == {"kind": "platform"}


@pytest.mark.requirement("WF-PLA-0160-A")
def test_setting_the_hours_per_day_to_seven_writes_the_three_constants_under_their_own_counter(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j »… vaut quatorze
    # heures » : the part of it the service keeps — the constant — is 7, its counter 2, its author
    # the caller's. The recalculation of the plannings is EP-06's.
    with database.transaction() as session:
        install_duration_units(session, PLATFORM)
    sent = {"hours_per_day": "7", "hours_per_week": "35", "days_per_month": "20", "lock_version": 1}
    response = api.put(UNITS, headers=sessions.changing, json=sent)
    assert response.status_code == 200
    body = response.json()
    assert constants(body) == ["7", "35", "20"]
    assert body["lock_version"] == 2
    assert body["audit"]["updated_by"]["kind"] == "user"
    assert body["audit"]["created_by"] == {"kind": "platform"}
    # The session exposes no account id: the author is an existing account, not the platform.
    with database.transaction() as session:
        author = session.get(UserAccount, UUID(body["audit"]["updated_by"]["user_id"]))
        assert author is not None
    assert body["audit"]["updated_at"] >= body["audit"]["created_at"]
    stale = api.put(UNITS, headers=sessions.changing, json=sent)
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    assert api.get(UNITS, headers=sessions.without).json()["hours_per_day"] == "7"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_constant_that_is_not_strictly_positive_is_refused_and_nothing_is_written(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    with database.transaction() as session:
        install_duration_units(session, PLATFORM)
    zero = {
        "hours_per_day": "0",
        "hours_per_week": "40",
        "days_per_month": "0.0",
        "lock_version": 1,
    }
    status, code, _, fields = refusal(api.put(UNITS, headers=sessions.changing, json=zero))
    assert (status, code) == (422, "VALIDATION_FAILED")
    assert fields == [
        {"pointer": "/hours_per_day", "code": "DURATION_UNIT_NOT_POSITIVE"},
        {"pointer": "/days_per_month", "code": "DURATION_UNIT_NOT_POSITIVE"},
    ]
    # The 422 is judged before the version is read: the stale counter below never shows as 412.
    stale = {**zero, "hours_per_day": "-8", "days_per_month": "20", "lock_version": 9}
    negative = {**zero, "hours_per_day": "-8", "days_per_month": "20"}
    for sent, pointer in (
        (negative, "/hours_per_day"),
        ({**negative, "hours_per_day": "-0"}, "/hours_per_day"),
        ({**negative, "hours_per_day": "-0.0"}, "/hours_per_day"),
        ({**negative, "hours_per_day": "abc"}, "/hours_per_day"),
        (stale, "/hours_per_day"),
    ):
        refused = api.put(UNITS, headers=sessions.changing, json=sent)
        assert refusal(refused)[:2] == (422, "VALIDATION_FAILED")
        assert refusal(refused)[3] == [{"pointer": pointer, "code": "VALIDATION_FAILED"}]
    with database.transaction() as session:
        read = get_duration_units(session)
    assert (read.units.hours_per_day, read.lock_version) == (Decimal(8), 1)


@pytest.mark.requirement("WF-REF-0110-A")
@pytest.mark.requirement("WF-PLA-0160-A")
def test_the_calendars_and_the_constants_are_written_by_who_may_change_the_resource_settings(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    with database.transaction() as session:
        install_duration_units(session, PLATFORM)
    calendar_id = seed(database, "Semaine standard", default=True)
    units = {
        "hours_per_day": "7",
        "hours_per_week": "35",
        "days_per_month": "20",
        "lock_version": 1,
    }
    body = {"label": "X", "weekly_hours": week()}
    writes = [
        ("POST", CALENDARS, body),
        ("PATCH", f"{CALENDARS}/{calendar_id}", {**body, "lock_version": 1}),
        ("PUT", f"{CALENDARS}/{calendar_id}/default", {"lock_version": 1}),
        ("PUT", f"{CALENDARS}/{calendar_id}/activation", {"is_active": True, "lock_version": 1}),
        ("PUT", UNITS, units),
    ]
    for headers in (sessions.without, sessions.reading):
        for method, path, sent in writes:
            response = api.request(method, path, headers=headers, json=sent)
            assert refusal(response)[:3] == (
                403,
                "PERMISSION_MISSING",
                {"missing_permission": "resource_settings.write"},
            )
    with database.transaction() as session:
        assert get_duration_units(session).lock_version == 1


@pytest.mark.requirement("WF-DAT-0070-A")
def test_the_authors_of_a_calendar_are_named_by_the_accounts_that_created_and_changed_it(
    api: ContractClient,
    database: Database,
    reference_sessions: ReferenceSessions,
) -> None:
    # Two accounts of the same part, told apart by their names: the first creates, the second
    # changes; the audit and the list name each as the contract does (``kind`` user).
    first = reference_sessions("resource_settings").changing
    second = reference_sessions("resource_settings").changing
    created = post(api, first, "Semaine standard")
    changed_by = api.patch(
        f"{CALENDARS}/{created['calendar_id']}",
        headers=second,
        json={"label": "Semaine revue", "weekly_hours": week(), "lock_version": 1},
    )
    assert changed_by.status_code == 200
    audit = changed_by.json()["audit"]
    author, editor = audit["created_by"], audit["updated_by"]
    assert (author["kind"], editor["kind"]) == ("user", "user")
    assert author["user_id"] != editor["user_id"]
    with database.transaction() as session:
        for who, first_name in ((author, "Alice"), (editor, "Bruno")):
            session.execute(
                update(UserAccount)
                .where(UserAccount.id == UUID(who["user_id"]))
                .values(first_name=first_name, last_name="Durand")
            )
    named = listing(api, first)["items"][0]["audit"]
    assert (named["created_by"]["display_name"], named["updated_by"]["display_name"]) == (
        "Alice Durand",
        "Bruno Durand",
    )
    assert (named["created_by"]["user_id"], named["updated_by"]["user_id"]) == (
        author["user_id"],
        editor["user_id"],
    )


def load(service_database_url: str) -> int:
    """Run the loader of the witness on the database of the test; give its status."""
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    return load_witness(settings)


def example_items() -> list[dict[str, Any]]:
    """Read the calendars of the example of the contract the witness is made of."""
    document = json.loads((WITNESS / "calendars_with_inactive.json").read_text(encoding="utf-8"))
    return document["value"]["items"]


def identifier(calendar: dict[str, Any]) -> str:
    """Give the identifier of a calendar read, the key of the order two lists are compared in."""
    return str(calendar["calendar_id"])


def without_audit(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give calendars without their audit, which a loading dates and signs as itself.

    The counter of writes counts those of the roles that reopen a calendar the time of being
    attached to it (#2131): as the other lists, it is left out.
    """
    unshared = {"audit", "lock_version"}
    return [{name: each[name] for name in each if name not in unshared} for each in items]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loads_the_calendars_and_designates_its_default_one(
    api: ContractClient, database: Database, sessions: PartSessions, service_database_url: str
) -> None:
    # `load-witness` writes `calendars_with_inactive.json` with its identifiers and its default
    # calendar, the one the platform held losing the designation, then deactivates the one it says
    # deactivated (#2131); the list reads back the example of the contract, the audit columns
    # apart. A second loading writes nothing.
    held = seed(database, "Installé", default=True)
    assert load(service_database_url) == 0
    example = example_items()
    wanted = {each["calendar_id"] for each in example}
    read = listing(api, sessions.changing, "include_inactive=true")["items"]
    ours = sorted((each for each in read if each["calendar_id"] in wanted), key=identifier)
    assert without_audit(ours) == without_audit(sorted(example, key=identifier))
    assert [each["label"] for each in read if each["is_default"]] == ["Semaine standard"]
    with database.transaction() as session:
        retired = read_calendar(session, held)
    assert (retired.is_default, retired.lock_version) == (False, 2)
    assert load(service_database_url) == 0
    assert listing(api, sessions.changing, "include_inactive=true")["items"] == read


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_stops_on_a_calendar_that_bears_an_identifier_of_its_own(
    database: Database, service_database_url: str
) -> None:
    # Half loaded: one calendar of the witness is there and not the other; the command stops, and
    # writes nothing of the missing one.
    seed(database, "Autre", identifier=UUID(example_items()[0]["calendar_id"]))
    assert load(service_database_url) == 1
    with database.transaction() as session:
        page = list_calendars(session, CalendarFilters(), CalendarSort(), CalendarWindow(10, 0))
    assert [each.label for each in page.calendars] == ["Autre"]
