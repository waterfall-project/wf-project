# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates (US-0830, WF-REF-0050, 0060), through the service.

The service is loaded with the witness by its command, and read by three sessions of the cost
settings (``reference_sessions``): one holding nothing of them, one that reads them, one that
changes them. Every answer is checked against the contract (``ContractClient``); the grid is
compared with the examples the faux back serves, played on the witness loaded.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from cost_settings_examples import (
    CATEGORIES,
    LABOUR,
    NON_LABOUR,
    PROVISION,
    TYPES,
    commands,
    deactivate,
    example,
    new_category,
    new_type,
    pointers,
    refusal,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.cost_settings.tables import HourlyRate

if TYPE_CHECKING:
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

GRID = "/api/v1/reference/hourly-rates"
CHANGE = "cost_settings.write"
READ = "cost_settings.read"
# MO-001, the electrical engineering of the examples: a rate from 2012 to 2026.
ELECTRICAL = UUID("01926f3a-7c00-7000-8000-000000000402")
# MO-003, the first mechanical engineering: its rates start in 2016 (15 ans moins quatre).
MECHANICAL = UUID("01926f3a-7c00-7000-8000-000400000000")
UNKNOWN = "7d1e5b0a-3c94-4f2e-9a68-5b20c4e1f9d3"


@pytest.fixture
def sessions(witness: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the cost settings on a service loaded with the witness."""
    del witness
    return reference_sessions("cost_settings")


def rates_url(category_id: object) -> str:
    """Give the address of the rates of a category."""
    return f"{CATEGORIES}/{category_id}/hourly-rates"


def rate_url(category_id: object, year: int) -> str:
    """Give the address of the rate of a category for a year."""
    return f"{rates_url(category_id)}/{year}"


def grid(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the grid by a session, the query given, and expect it."""
    response = api.get(f"{GRID}?{query}", headers=headers)
    assert response.status_code == 200
    return response.json()


def codes(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the codes of the rows of the grid a query keeps, in their order."""
    return [row["code"] for row in grid(api, headers, query)["rows"]]


def shown(page: dict[str, Any]) -> dict[str, Any]:
    """Give a page of the grid as the examples and the service agree on it.

    Without the audit of the cells (the loading is the platform's, at its instant); the counters
    are kept.
    """
    return {
        **page,
        "rows": [
            {
                **row,
                "cells": [
                    None if cell is None else {k: v for k, v in cell.items() if k != "audit"}
                    for cell in row["cells"]
                ],
            }
            for row in page["rows"]
        ],
    }


def rate_of(api: ContractClient, headers: dict[str, str], category_id: object, year: int) -> Any:
    """Read the rate of a category for a year; ``None`` if it bears none."""
    found = [
        r for r in api.get(rates_url(category_id), headers=headers).json() if r["year"] == year
    ]
    return found[0] if found else None


def amount(value: str, **more: object) -> dict[str, object]:
    """Give the body of a rate."""
    return {"amount": value, **more}


def labour_category(api: ContractClient, headers: dict[str, str], code: str) -> Any:
    """Create a category of labour under the nature of labour of the witness."""
    return new_category(api, headers, code, LABOUR)


def category_of(api: ContractClient, headers: dict[str, str], code: str) -> Any:
    """Read a category by its code, deactivated ones included."""
    response = api.get(
        f"{CATEGORIES}?include_inactive=true&search={code}&limit=500", headers=headers
    )
    (found,) = [item for item in response.json()["items"] if item["code"] == code]
    return found


@pytest.mark.requirement("WF-REF-0050-A")
@pytest.mark.requirement("WF-REF-0060-A")
def test_the_witness_grid_is_read_as_the_example_the_faux_back_serves(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The 150 categories of labour on 15 years, in one page of 500, by a session that reads.
    volume = example("volume/hourly_rate_grid")
    read = grid(api, sessions.reading, "limit=500")
    assert shown(read) == shown(volume)
    assert len(read["rows"]) == 150
    # The session that changes reads the same grid.
    assert shown(grid(api, sessions.changing, "limit=500")) == shown(volume)
    assert all(len(row["cells"]) == len(read["years"]) for row in read["rows"])
    # The first page of fifty by the rate of 2026, descending, then the rates from 99.12 on.
    by_rate = grid(api, sessions.reading, "rate_year=2026&sort_by=rate.2026&sort_order=desc")
    assert shown(by_rate) == shown(example("volume/hourly_rate_grid_by_rate"))
    bounded = grid(api, sessions.reading, "rate_year=2026&rate_min=99.12")
    assert shown(bounded) == shown(example("volume/hourly_rate_grid_bounded"))


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_grid_is_unknown_to_a_session_that_does_not_read_the_cost_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    expected = example("hourly_rate_grid_not_readable")
    for url in (GRID, rates_url(ELECTRICAL)):
        response = api.get(url, headers=sessions.without)
        assert (response.status_code, response.json()["code"]) == (404, expected["code"])


@pytest.mark.requirement("WF-REF-0050-A")
@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_categories_of_the_grid_ask_for_the_permission_to_change_not_to_read(
    api: ContractClient, sessions: PartSessions
) -> None:
    # Decision of the author of 2026-11-06 (#2084, option A): ``include_inactive`` and
    # ``is_active=false`` are read under ``cost_settings.write``, as the frozen contract says;
    # the grid itself is read under ``cost_settings.read``.
    for query in ("include_inactive=true", "is_active=false"):
        denied = api.get(f"{GRID}?{query}", headers=sessions.reading)
        assert refusal(denied) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})
        # Unknown before it is forbidden: a session that cannot read the grid is told 404.
        assert api.get(f"{GRID}?{query}", headers=sessions.without).status_code == 404
        assert api.get(f"{GRID}?{query}", headers=sessions.changing).status_code == 200


@pytest.mark.requirement("WF-REF-0050-A")
@pytest.mark.requirement("WF-REF-0060-A")
def test_the_years_are_those_of_the_whole_grid_whatever_the_page_the_search_the_bounds_or_the_sort(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.reading
    every = grid(api, headers)["years"]
    assert every == list(range(2012, 2027))
    for query in (
        "limit=1&offset=140",
        "search=MO-003",
        "search=zzzz",
        "rate_year=2026&rate_min=119.9",
        "sort_by=rate.2020&sort_order=desc",
    ):
        assert grid(api, headers, query)["years"] == every
    nothing = grid(api, headers, "search=zzzz")
    assert (nothing["rows"], nothing["meta"]["total"]) == ([], 0)
    beyond = grid(api, headers, "limit=10&offset=500")
    assert (beyond["rows"], beyond["meta"]["total"]) == ([], 150)


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_grid_gives_a_row_per_category_of_labour_active_unless_the_deactivated_are_asked(
    api: ContractClient, sessions: PartSessions
) -> None:
    changing = sessions.changing
    # Only the categories of labour have a row: the ones of the other natures, never.
    # The 150 categories of labour of the witness are all the rows: no other nature adds one.
    assert grid(api, changing, "include_inactive=true&limit=1")["meta"]["total"] == 150
    old = labour_category(api, changing, "OLD")
    assert (
        api.put(
            rate_url(old["cost_category_id"], 2030), headers=changing, json=amount("50")
        ).status_code
        == 200
    )
    off = {"is_active": False, "lock_version": old["lock_version"]}
    api.put(f"{CATEGORIES}/{old['cost_category_id']}/activation", headers=changing, json=off)
    # The year of a deactivated category is a column only when the deactivated are in the read.
    plain = grid(api, sessions.reading)
    assert plain["years"][-1] == 2026
    assert codes(api, changing, "search=OLD") == []
    for query in ("include_inactive=true&search=OLD", "is_active=false"):
        read = grid(api, changing, query)
        assert read["years"] == [*range(2012, 2027), 2030]
        row = next(r for r in read["rows"] if r["code"] == "OLD")
        assert (row["is_active"], [c and c["amount"] for c in row["cells"]]) == (
            False,
            [None] * 15 + ["50.00"],
        )
    assert codes(api, changing, "is_active=false") == ["OLD"]
    # Deactivated after the active in the ascending order of the state.
    ordered = grid(api, changing, "include_inactive=true&sort_by=is_active&limit=1&offset=150")
    assert ([r["code"] for r in ordered["rows"]], ordered["meta"]["total"]) == (["OLD"], 151)
    assert (
        codes(api, changing, "include_inactive=true&sort_by=is_active&sort_order=desc")[0] == "OLD"
    )


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_grid_is_searched_by_code_and_label_and_sorted_by_code_label_state_or_rate(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    assert codes(api, headers, "search=mo-003") == ["MO-003"]
    label = next(r["label"] for r in grid(api, headers, "search=MO-003")["rows"])
    assert "MO-003" in codes(api, headers, f"search={label}")
    # The accounting code is no column of the grid: it is not searched.
    accounting = category_of(api, headers, "MO-001")["accounting_code"]
    assert codes(api, headers, f"search={accounting}") == []
    by_label = grid(api, headers, "sort_by=label&limit=500")["rows"]
    assert [r["label"] for r in by_label] == sorted(r["label"] for r in by_label)
    assert codes(api, headers, "sort_by=code&sort_order=desc&limit=2") == ["MO-150", "MO-149"]
    # A category without a rate that year comes after the others ascending, before descending.
    bare = labour_category(api, headers, "BARE")
    asc = grid(api, headers, "sort_by=rate.2026&limit=500")["rows"]
    desc = grid(api, headers, "sort_by=rate.2026&sort_order=desc&limit=500")["rows"]
    assert (asc[-1]["code"], desc[0]["code"]) == ("BARE", "BARE")
    rates = [float(r["cells"][-1]["amount"]) for r in asc[:-1]]
    assert rates == sorted(rates)
    assert [r["cells"][-1]["amount"] for r in desc[1:]] == [
        r["cells"][-1]["amount"] for r in asc[:-1]
    ][::-1]
    # A year the grid does not carry leaves the order of the code; bare categories keep the code.
    assert codes(api, headers, "sort_by=rate.2099&limit=500") == sorted(
        codes(api, headers, "limit=500")
    )
    assert bare["code"] == "BARE"


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_bounds_of_the_rate_keep_the_categories_that_bear_one_that_year_and_are_included(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.reading
    mo_001 = "80.00"
    only = grid(api, headers, f"rate_year=2026&rate_min={mo_001}&rate_max={mo_001}&search=MO-001")
    assert [r["code"] for r in only["rows"]] == ["MO-001"]
    # A category without a rate that year is kept by no bound: MO-003 bears none before 2016.
    assert codes(api, headers, "rate_year=2013&rate_max=1000&search=MO-003") == []
    assert codes(api, headers, "rate_year=2016&rate_max=1000&search=MO-003") == ["MO-003"]
    # The year alone filters and sorts nothing.
    assert grid(api, headers, "rate_year=2013")["meta"]["total"] == 150
    assert codes(api, headers, "rate_year=2013") == codes(api, headers)
    assert grid(api, headers, "rate_year=2026&rate_max=0.5")["meta"]["total"] == 0


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_bound_malformed_inverted_or_without_its_year_and_a_sort_unknown_are_refused(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.reading
    inverted = api.get(f"{GRID}?rate_year=2026&rate_min=100&rate_max=90", headers=headers)
    fixture = example("hourly_rate_grid_bounds_inverted")
    assert (inverted.status_code, inverted.json()["code"]) == (422, fixture["code"])
    assert pointers(inverted) == [("/query/rate_max", "VALUE_OUT_OF_RANGE", {"minimum": "100"})]
    missing = api.get(f"{GRID}?rate_min=100", headers=headers)
    assert missing.status_code == 422
    assert pointers(missing) == [("/query/rate_year", "VALUE_REQUIRED", {})]
    malformed = api.get(f"{GRID}?rate_year=2026&rate_min=abc&rate_max=1.234", headers=headers)
    assert pointers(malformed) == [
        ("/query/rate_min", "NUMBER_INVALID", {}),
        ("/query/rate_max", "NUMBER_INVALID", {}),
    ]
    # A digit that is no ASCII one is no money; a valid money of any length is no malformation.
    arabic = api.get(f"{GRID}?rate_year=2026&rate_min=\u0663", headers=headers)
    assert pointers(arabic) == [("/query/rate_min", "NUMBER_INVALID", {})]
    huge = api.get(f"{GRID}?rate_year=2026&rate_min={'9' * 21}", headers=headers)
    assert huge.status_code == 200
    assert huge.json()["meta"]["total"] == 0
    for query in ("sort_by=rate.1999", "sort_by=accounting_code", "rate_year=2101"):
        assert api.get(f"{GRID}?{query}", headers=headers).status_code == 422


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_rates_of_a_category_are_listed_by_year_as_the_example_the_faux_back_serves(
    api: ContractClient, sessions: PartSessions
) -> None:
    expected = cast("list[dict[str, Any]]", example("volume/hourly_rates"))
    read = api.get(rates_url(ELECTRICAL), headers=sessions.reading).json()
    unshared = {"audit"}
    assert [{k: v for k, v in r.items() if k not in unshared} for r in read] == [
        {k: v for k, v in r.items() if k not in unshared} for r in expected
    ]
    # A category of another nature bears none; an unknown one is unknown.
    bare = new_category(api, sessions.changing, "OUT", NON_LABOUR)
    assert api.get(rates_url(bare["cost_category_id"]), headers=sessions.reading).json() == []
    assert api.get(rates_url(UNKNOWN), headers=sessions.reading).status_code == 404


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_rate_is_set_without_a_version_once_then_corrected_at_the_version_read(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    entered = api.put(rate_url(MECHANICAL, 2015), headers=headers, json=amount("85.48"))
    assert entered.status_code == 200
    expected = example("hourly_rate_entered")
    assert {k: v for k, v in entered.json().items() if k != "audit"} == {
        k: v for k, v in expected.items() if k != "audit"
    }
    assert entered.json()["audit"]["created_by"]["kind"] == "user"
    # A second first-time setting for a year that bears a rate is refused, nothing written.
    again = api.put(rate_url(MECHANICAL, 2016), headers=headers, json=amount("12.00"))
    assert refusal(again) == (409, example("hourly_rate_already_entered")["code"], {})
    assert rate_of(api, headers, MECHANICAL, 2016)["amount"] == "86.98"
    # The correction at the version read advances it; a stale counter is refused, nothing written.
    corrected = api.put(
        rate_url(MECHANICAL, 2016), headers=headers, json=amount("87.20", lock_version=1)
    )
    assert corrected.status_code == 200
    assert (corrected.json()["amount"], corrected.json()["lock_version"]) == ("87.20", 2)
    stale = api.put(
        rate_url(MECHANICAL, 2016), headers=headers, json=amount("1.00", lock_version=1)
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    assert rate_of(api, headers, MECHANICAL, 2016)["amount"] == "87.20"
    # A correction of a year that bears no rate has nothing to correct.
    nothing = api.put(
        rate_url(MECHANICAL, 2014), headers=headers, json=amount("1.00", lock_version=1)
    )
    assert nothing.status_code == 404
    # Read by a session that only reads, the rate is the one written; it cannot write.
    assert rate_of(api, sessions.reading, MECHANICAL, 2015)["amount"] == "85.48"


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_rate_is_refused_without_the_permission_to_change_the_cost_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    for headers in (sessions.without, sessions.reading):
        denied = api.put(rate_url(MECHANICAL, 2015), headers=headers, json=amount("85.48"))
        assert refusal(denied) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})
    assert rate_of(api, sessions.changing, MECHANICAL, 2015) is None


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_rate_for_a_category_outside_labour_is_refused_without_fields(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    outside = [
        new_category(api, headers, "NON", NON_LABOUR),
        new_category(api, headers, "PRV", PROVISION),
    ]
    for each in outside:
        response = api.put(
            rate_url(each["cost_category_id"], 2026), headers=headers, json=amount("50")
        )
        assert refusal(response) == (422, "LABOUR_CATEGORY_REQUIRED", {})
        assert "fields" not in response.json()
        assert api.get(rates_url(each["cost_category_id"]), headers=headers).json() == []
    unknown = api.put(rate_url(UNKNOWN, 2026), headers=headers, json=amount("50"))
    assert unknown.status_code == 404


@pytest.mark.requirement("WF-REF-0050-A")
@pytest.mark.parametrize("value", ["0", "0.00", "0.0", "-1", "-0.01"])
def test_a_rate_nil_or_negative_is_refused_at_its_amount_naming_the_smallest(
    api: ContractClient, sessions: PartSessions, value: str
) -> None:
    response = api.put(rate_url(MECHANICAL, 2015), headers=sessions.changing, json=amount(value))
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert pointers(response) == [("/amount", "VALUE_OUT_OF_RANGE", {"minimum": "0.01"})]
    assert rate_of(api, sessions.changing, MECHANICAL, 2015) is None


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_smallest_rate_is_set_and_one_beyond_the_column_is_refused_naming_the_greatest(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    smallest = api.put(rate_url(MECHANICAL, 2015), headers=headers, json=amount("0.01"))
    assert (smallest.status_code, smallest.json()["amount"]) == (200, "0.01")
    greatest = api.put(rate_url(MECHANICAL, 2014), headers=headers, json=amount("9999999999.99"))
    assert (greatest.status_code, greatest.json()["amount"]) == (200, "9999999999.99")
    over = api.put(rate_url(MECHANICAL, 2013), headers=headers, json=amount("10000000000"))
    assert pointers(over) == [("/amount", "VALUE_OUT_OF_RANGE", {"maximum": "9999999999.99"})]
    # A year outside the bounds of the contract names no rate.
    assert api.put(rate_url(MECHANICAL, 2101), headers=headers, json=amount("1")).status_code == 422


@pytest.mark.requirement("WF-REF-0060-A")
def test_the_first_rate_of_a_year_adds_its_column_empty_and_leaves_the_other_years_as_they_were(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    before = grid(api, headers, "limit=500")
    assert 2011 not in before["years"]
    added = api.put(rate_url(ELECTRICAL, 2011), headers=headers, json=amount("57.50"))
    expected = example("hourly_rate_added_year")
    assert {k: v for k, v in added.json().items() if k != "audit"} == {
        k: v for k, v in expected.items() if k != "audit"
    }
    after = grid(api, headers, "limit=500")
    assert after["years"] == [2011, *before["years"]]
    assert len(after["rows"]) == len(before["rows"])
    for old, new in zip(before["rows"], after["rows"], strict=True):
        assert new["code"] == old["code"]
        # The new column is empty but for the rate set; the cells of the others are unchanged.
        assert new["cells"][1:] == old["cells"]
        first = new["cells"][0]
        assert (first is None) == (new["cost_category_id"] != str(ELECTRICAL))
    assert after["rows"][0]["cells"][0]["amount"] == "57.50"


@pytest.mark.requirement("WF-REF-0050-A")
def test_the_first_rate_of_a_category_makes_the_change_of_its_nature_and_of_its_kind_unavailable(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "RATED")
    created = new_category(api, headers, "RTD", nature["cost_type_id"])
    identifier = created["cost_category_id"]
    other = new_type(api, headers, "OTHER", "non_labor")

    def lists() -> tuple[Any, Any]:
        category = category_of(api, headers, "RTD")
        found = api.get(f"{TYPES}?search=RATED", headers=headers).json()["items"]
        (this,) = [item for item in found if item["code"] == "RATED"]
        return category, this

    category, this = lists()
    assert commands(category)[1] == ("change_cost_type", True, [])
    assert commands(this)[1] == ("change_kind", True, [])
    assert (
        api.put(rate_url(identifier, 2026), headers=headers, json=amount("70")).status_code == 200
    )
    category, this = lists()
    assert commands(category)[1] == ("change_cost_type", False, ["cost_category_unrated"])
    assert commands(this)[1] == ("change_kind", False, ["cost_type_unrated"])
    # The refusals say the same, by the very rate the lists read.
    move = {
        "code": "RTD",
        "label": "RTD",
        "accounting_code": created["accounting_code"],
        "cost_type_id": other["cost_type_id"],
        "lock_version": category["lock_version"],
    }
    moved = api.patch(f"{CATEGORIES}/{identifier}", headers=headers, json=move)
    assert refusal(moved) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "cost_category_unrated"},
    )
    recast = {
        "code": "RATED",
        "label": "RATED",
        "kind": "provision",
        "lock_version": this["lock_version"],
    }
    kind = api.patch(f"{TYPES}/{nature['cost_type_id']}", headers=headers, json=recast)
    assert kind.status_code == 409
    assert kind.json()["params"]["missing_condition"] == "cost_type_unrated"
    assert [c["code"] for c in kind.json()["params"]["cost_categories"]] == ["RTD"]
    # Another category of the nature, unrated, stays free to leave: the rule is on the rated one.
    free = new_category(api, headers, "FRE", nature["cost_type_id"])
    assert commands(category_of(api, headers, "FRE"))[1] == ("change_cost_type", True, [])
    assert free["code"] == "FRE"
    # A correction does not undo it: a rate never goes.
    again = api.put(rate_url(identifier, 2026), headers=headers, json=amount("71", lock_version=1))
    assert again.status_code == 200
    assert commands(lists()[0])[1][1] is False


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_deactivated_nature_does_not_hide_the_rates_of_its_categories(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "SHUT")
    created = new_category(api, headers, "SHT", nature["cost_type_id"])
    set_one = api.put(
        rate_url(created["cost_category_id"], 2026), headers=headers, json=amount("70")
    )
    assert set_one.status_code == 200
    assert deactivate(api, headers, nature).status_code == 200
    assert [
        r["year"] for r in api.get(rates_url(created["cost_category_id"]), headers=headers).json()
    ] == [2026]
    assert "SHT" in codes(api, headers, "include_inactive=true&limit=500")
    assert "SHT" not in codes(api, headers, "limit=500")


@pytest.mark.requirement("WF-REF-0050-A")
def test_two_simultaneous_first_settings_of_one_year_leave_one_rate_and_one_refusal(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # Both wait for the lock of the natures another transaction holds, then one takes it: the
    # other finds the year taken and is refused, not written twice.
    headers = sessions.changing
    with ThreadPoolExecutor(2) as pool, Session(database.engine) as holding:
        holding.execute(select(func.pg_advisory_xact_lock(NATURES_LOCK)))
        first = pool.submit(
            api.put, rate_url(ELECTRICAL, 2011), headers=headers, json=amount("1.00")
        )
        second = pool.submit(
            api.put, rate_url(ELECTRICAL, 2011), headers=headers, json=amount("2.00")
        )
        wait_for_a_lock(database, 2)
        assert not first.done()
        assert not second.done()
        holding.commit()
        answers = sorted(
            [first.result(timeout=10).status_code, second.result(timeout=10).status_code]
        )
    assert answers == [200, 409]
    with database.transaction() as session:
        written = session.scalars(
            select(func.count()).select_from(HourlyRate).where(HourlyRate.year == 2011)
        ).one()
    assert written == 1


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_rate_set_while_the_kind_of_its_nature_changes_never_leaves_a_rate_outside_labour(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # The change of the kind and the setting of a rate both ask for the lock of the natures: the
    # one that takes it first decides, and the other sees its effect — never both succeeding.
    headers = sessions.changing
    nature = new_type(api, headers, "FLIP")
    created = new_category(api, headers, "FLP", nature["cost_type_id"])
    recast = {
        "code": "FLIP",
        "label": "FLIP",
        "kind": "non_labor",
        "lock_version": nature["lock_version"],
    }
    with ThreadPoolExecutor(2) as pool, Session(database.engine) as holding:
        holding.execute(select(func.pg_advisory_xact_lock(NATURES_LOCK)))
        setting = pool.submit(
            api.put, rate_url(created["cost_category_id"], 2026), headers=headers, json=amount("9")
        )
        flipping = pool.submit(
            api.patch, f"{TYPES}/{nature['cost_type_id']}", headers=headers, json=recast
        )
        wait_for_a_lock(database, 2)
        holding.commit()
        set_answer = setting.result(timeout=10)
        flip_answer = flipping.result(timeout=10)
    outcome = (set_answer.status_code, flip_answer.status_code)
    assert outcome in {(200, 409), (422, 200)}
    with database.transaction() as session:
        rates = session.scalars(
            select(func.count()).select_from(HourlyRate).where(HourlyRate.year == 2026)
        ).one()
    assert rates == 150 + (1 if outcome == (200, 409) else 0)
