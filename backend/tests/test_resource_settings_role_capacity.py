# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours a month of a role, calculated from its headcount and its calendar (US-2410).

Through the service loaded with the witness: the roles and the calendars are created and changed by
the API, and the hours read back, listed, bounded and sorted as ``listResourceRoles`` gives them.
"""

from typing import TYPE_CHECKING, Any

import pytest
from test_resource_settings_roles import BE_ELEC, ROLES, change_of, listed, new_role, role

if TYPE_CHECKING:
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@pytest.fixture
def sessions(witness: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the resource settings on a service loaded with the witness."""
    del witness
    return reference_sessions("resource_settings")


def calendar(api: ContractClient, headers: dict[str, str], label: str, *hours: str) -> str:
    """Create a calendar by the service, its hours from Monday on; give its identifier."""
    sent = {"label": label, "weekly_hours": dict(zip(DAYS, hours, strict=True))}
    response = api.post(CALENDARS, headers=headers, json=sent)
    assert response.status_code == 201, response.text
    return response.json()["calendar_id"]


def created(
    api: ContractClient, headers: dict[str, str], code: str, calendar_id: str, headcount: str
) -> dict[str, Any]:
    """Create a role under the electrical office on a calendar, with its headcount; give it."""
    sent = new_role(
        code=code,
        label=f"Rôle {code}",
        org_node_id=BE_ELEC,
        calendar_id=calendar_id,
        capacity={"headcount": headcount},
    )
    response = api.post(ROLES, headers=headers, json=sent)
    assert response.status_code == 201, response.text
    return response.json()


def hours_of(api: ContractClient, headers: dict[str, str], query: str) -> list[tuple[str, str]]:
    """Give the code and the hours a month of each role a query keeps, in their order."""
    return [
        (each["code"], each["capacity"]["monthly_hours"])
        for each in listed(api, headers, query)["items"]
    ]


@pytest.mark.requirement("WF-REF-0100-A")
def test_two_people_on_thirty_five_hours_a_week_have_303_33_hours_and_half_a_person_75_83(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « Un rôle de deux personnes sur un calendrier de 35 heures par semaine dispose de
    # 2 * 35 * 52 / 12, soit environ 303,33 heures par mois ; un effectif de 0,5 sur le même
    # calendrier en dispose de 75,83. » — as the service answers a creation, and as it lists, bounds
    # and sorts the roles, the hours calculated by the database.
    headers = sessions.changing
    week = calendar(api, headers, "Semaine de 35 heures", "7", "7", "7", "7", "7", "0", "0")
    two = created(api, headers, "DEUX", week, "2")
    half = created(api, headers, "DEMI", week, "0.5")
    assert two["capacity"] == {"monthly_hours": "303.33", "headcount": "2"}
    assert half["capacity"] == {"monthly_hours": "75.83", "headcount": "0.5"}
    on_week = f"calendar_id={week}&sort_by=monthly_hours"
    assert hours_of(api, headers, on_week) == [("DEMI", "75.83"), ("DEUX", "303.33")]
    assert hours_of(api, headers, f"{on_week}&sort_order=desc") == [
        ("DEUX", "303.33"),
        ("DEMI", "75.83"),
    ]
    assert hours_of(api, headers, f"{on_week}&monthly_hours_min=75.84") == [("DEUX", "303.33")]
    assert hours_of(api, headers, f"{on_week}&monthly_hours_max=75.83") == [("DEMI", "75.83")]
    bounded = listed(api, headers, f"{on_week}&monthly_hours_min=75.83&monthly_hours_max=303.33")
    assert bounded["meta"]["total"] == 2


@pytest.mark.requirement("WF-REF-0100-A")
def test_the_hours_of_a_role_follow_its_calendar_at_the_next_reading(
    api: ContractClient, sessions: PartSessions
) -> None:
    # Propre à l'US : « les heures d'un rôle suivent le calendrier qu'il porte : en changer, ou
    # changer ses heures hebdomadaires, change la capacité à la lecture suivante ».
    headers = sessions.changing
    week = calendar(api, headers, "Semaine de 35 heures", "7", "7", "7", "7", "7", "0", "0")
    halves = calendar(api, headers, "Demi-journées", "4", "4", "4", "4", "4", "0", "0")
    created(api, headers, "DEUX", week, "2")
    assert role(api, headers, "DEUX")["capacity"]["monthly_hours"] == "303.33"
    # The hours of its calendar changed, at its first version: 2 * 40 * 52 / 12.
    sent = {
        "label": "Semaine de 35 heures",
        "weekly_hours": dict(zip(DAYS, ("8", "8", "8", "8", "8", "0", "0"), strict=True)),
        "lock_version": 1,
    }
    changed = api.patch(f"{CALENDARS}/{week}", headers=headers, json=sent)
    assert changed.status_code == 200, changed.text
    assert role(api, headers, "DEUX")["capacity"]["monthly_hours"] == "346.67"
    # Another calendar given: 2 * 20 * 52 / 12, its headcount kept.
    current = role(api, headers, "DEUX")
    moved = api.patch(
        f"{ROLES}/{current['resource_role_id']}",
        headers=headers,
        json=change_of(current, calendar_id=halves),
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["capacity"] == {"monthly_hours": "173.33", "headcount": "2"}
    assert role(api, headers, "DEUX")["capacity"]["monthly_hours"] == "173.33"
    # Its headcount changed: 3 * 20 * 52 / 12.
    current = role(api, headers, "DEUX")
    grown = api.patch(
        f"{ROLES}/{current['resource_role_id']}",
        headers=headers,
        json=change_of(current, capacity={"headcount": "3"}),
    )
    assert grown.json()["capacity"] == {"monthly_hours": "260.00", "headcount": "3"}


@pytest.mark.requirement("WF-REF-0100-A")
def test_a_half_hundredth_rounds_to_the_even_in_the_view_its_bounds_and_its_sort(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The hours to the hundredth, a half to the even (docs/api/DECISIONS.md, « La capacité d'un
    # rôle »): 1.5 * 0.03 * 52 / 12 is 0.195, which rounds up to 0.20; 0.5 * 0.03 * 52 / 12 is
    # 0.065, which rounds down to 0.06 — not 0.07, as a half away from zero would. The bound and the
    # sort, in SQL, read the same value as the view.
    headers = sessions.changing
    thin = calendar(api, headers, "Trois centièmes", "0.03", "0", "0", "0", "0", "0", "0")
    created(api, headers, "UP", thin, "1.5")
    created(api, headers, "DOWN", thin, "0.5")
    on_thin = f"calendar_id={thin}&sort_by=monthly_hours"
    assert hours_of(api, headers, on_thin) == [("DOWN", "0.06"), ("UP", "0.20")]
    assert hours_of(api, headers, f"{on_thin}&monthly_hours_max=0.06") == [("DOWN", "0.06")]
    assert hours_of(api, headers, f"{on_thin}&monthly_hours_min=0.20") == [("UP", "0.20")]
