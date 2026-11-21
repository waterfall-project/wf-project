# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``listBackups`` filters and sorts every column, as the contract says (WF-IHM-0130, WF-IHM-0060).

The date by a period (``from`` included, ``to`` excluded), the origin and the verification by
lists, the mark, the size by its two bounds, included; the filters combine and ``meta.total``
counts the backups kept. Each of the five columns sorts, the date the latest first without a sort;
a tie is broken by the date, the latest first, then the identifier (US-2910/L2, #2231). A period or
bounds inverted are refused at their end, a malformed value at its own (422). Each person is an
account written around the service; every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from backup_rows import Row, days, recorded
from realm import KEY, TestRealm
from support import ContractClient, bearer

if TYPE_CHECKING:
    from waterfall.platform.database import Database

pytestmark = pytest.mark.story("US-2910")

BACKUPS = "/api/v1/backups"
READ = "backups.read"


@pytest.fixture
def reader(database: Database, realm: TestRealm) -> dict[str, str]:
    """Give the header of an account that reads the backups."""
    subject = f"subject-{uuid4()}"
    held = role(database, "Lecture des sauvegardes", permissions=(READ,))
    account(database, "Martin", "Claire", roles=(held,), idp_subject=subject)
    return bearer(realm.token(subject, KEY))


@pytest.fixture
def backups(database: Database) -> dict[str, UUID]:
    """Record five backups, each different in every column, and name them."""
    return {
        "a": recorded(database, days(1), Row("manual", "passed", 300, is_retained=True)),
        "b": recorded(database, days(2), Row("scheduled", "failed", 100)),
        "c": recorded(database, days(3), Row("scheduled", "passed", 500)),
        "d": recorded(database, days(4), Row("manual", "pending", 100, is_retained=True)),
        "e": recorded(database, days(5), Row("scheduled", "passed", 300)),
    }


def listed(
    api: ContractClient, headers: dict[str, str], query: str = ""
) -> tuple[list[UUID], dict[str, Any]]:
    """List the backups under a query: the identifiers in the order given, and the page's meta."""
    response = api.get(f"{BACKUPS}?{query}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    return [UUID(item["backup_id"]) for item in body["items"]], body["meta"]


def named(backups: dict[str, UUID], *names: str) -> list[UUID]:
    """Give the identifiers of the backups a test names, in the order it names them."""
    return [backups[name] for name in names]


@pytest.mark.requirement("WF-IHM-0130-A")
def test_without_a_filter_nor_a_sort_the_backups_are_listed_by_date_the_latest_first(
    api: ContractClient, reader: dict[str, str], backups: dict[str, UUID]
) -> None:
    ids, meta = listed(api, reader)
    assert ids == named(backups, "e", "d", "c", "b", "a")
    assert meta["total"] == 5


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_period_runs_from_its_start_included_to_its_end_excluded(
    api: ContractClient, reader: dict[str, str], backups: dict[str, UUID]
) -> None:
    ids, meta = listed(api, reader, "from=2026-10-02T01:00:00Z&to=2026-10-04T01:00:00Z")
    assert ids == named(backups, "c", "b")
    assert meta["total"] == 2
    assert listed(api, reader, "from=2026-10-05T01:00:00Z")[0] == named(backups, "e")
    assert listed(api, reader, "to=2026-10-01T01:00:00Z")[0] == []


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_origins_and_the_verifications_are_lists_and_the_mark_a_boolean(
    api: ContractClient, reader: dict[str, str], backups: dict[str, UUID]
) -> None:
    assert listed(api, reader, "origins=manual")[0] == named(backups, "d", "a")
    assert listed(api, reader, "origins=manual,scheduled")[1]["total"] == 5
    assert listed(api, reader, "verifications=passed,failed")[0] == named(
        backups, "e", "c", "b", "a"
    )
    assert listed(api, reader, "verifications=pending")[0] == named(backups, "d")
    assert listed(api, reader, "is_retained=true")[0] == named(backups, "d", "a")
    assert listed(api, reader, "is_retained=false")[0] == named(backups, "e", "c", "b")


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_bounds_of_the_size_are_included_and_the_filters_combine(
    api: ContractClient, reader: dict[str, str], backups: dict[str, UUID]
) -> None:
    assert listed(api, reader, "size_bytes_min=300")[0] == named(backups, "e", "c", "a")
    assert listed(api, reader, "size_bytes_max=100")[0] == named(backups, "d", "b")
    assert listed(api, reader, "size_bytes_min=100&size_bytes_max=300")[0] == named(
        backups, "e", "d", "b", "a"
    )
    combined = "origins=scheduled&verifications=passed&is_retained=false&size_bytes_min=300"
    ids, meta = listed(api, reader, f"{combined}&limit=1")
    assert (ids, meta["total"]) == (named(backups, "e"), 2)
    assert listed(api, reader, f"{combined}&limit=1&offset=1")[0] == named(backups, "c")


@pytest.mark.requirement("WF-IHM-0060-A")
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # The date: the latest first by default, the oldest first when it is asked ascending.
        ("sort_by=taken_at", "edcba"),
        ("sort_by=taken_at&sort_order=asc", "abcde"),
        # The size ascending by default, ties broken by the date, the latest first.
        ("sort_by=size_bytes", "dbeac"),
        ("sort_by=size_bytes&sort_order=desc", "ceadb"),
        # The verification in the order of its enumeration: pending, passed, failed.
        ("sort_by=verification", "decab"),
        ("sort_by=verification&sort_order=desc", "becad"),
        # The origin in the order of its enumeration: manual, scheduled.
        ("sort_by=origin", "daecb"),
        ("sort_by=origin&sort_order=desc", "ecbda"),
        # The mark: the backups marked first, in the ascending order.
        ("sort_by=is_retained", "daecb"),
        ("sort_by=is_retained&sort_order=desc", "ecbda"),
    ],
)
def test_each_column_sorts_and_a_tie_is_broken_by_the_date_the_latest_first(
    api: ContractClient,
    reader: dict[str, str],
    backups: dict[str, UUID],
    query: str,
    expected: str,
) -> None:
    ids, _ = listed(api, reader, query)
    assert ids == named(backups, *expected)


@pytest.mark.requirement("WF-IHM-0130-A")
def test_a_period_whose_end_precedes_its_start_is_refused_at_its_end_the_start_named(
    api: ContractClient, reader: dict[str, str]
) -> None:
    refused = api.get(
        f"{BACKUPS}?from=2026-06-03T14:00:00Z&to=2026-06-01T00:00:00Z", headers=reader
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "VALIDATION_FAILED"
    [fault] = refused.json()["fields"]
    assert (fault["pointer"], fault["code"]) == ("/query/to", "VALUE_OUT_OF_RANGE")
    assert fault["params"]["minimum"].startswith("2026-06-03T14:00:00")


@pytest.mark.requirement("WF-IHM-0130-A")
def test_bounds_of_the_size_inverted_are_refused_at_the_upper_one_the_lower_one_named(
    api: ContractClient, reader: dict[str, str]
) -> None:
    refused = api.get(
        f"{BACKUPS}?size_bytes_min=1300000000&size_bytes_max=1000000000", headers=reader
    )
    assert refused.status_code == 422
    assert refused.json()["fields"] == [
        {
            "pointer": "/query/size_bytes_max",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": 1300000000},
        }
    ]


@pytest.mark.requirement("WF-IHM-0130-A")
@pytest.mark.parametrize(
    ("query", "pointer", "code"),
    [
        ("from=yesterday", "/query/from", "DATE_INVALID"),
        ("to=2026-10-01", "/query/to", "DATE_INVALID"),
        ("size_bytes_min=-1", "/query/size_bytes_min", "NUMBER_INVALID"),
        ("size_bytes_max=lots", "/query/size_bytes_max", "NUMBER_INVALID"),
        ("origins=manual,sometimes", "/query/origins", "VALIDATION_FAILED"),
        ("verifications=", "/query/verifications", "VALIDATION_FAILED"),
        ("sort_by=label", "/query/sort_by", "VALIDATION_FAILED"),
    ],
)
def test_a_malformed_filter_is_refused_at_its_own_parameter(
    api: ContractClient, reader: dict[str, str], query: str, pointer: str, code: str
) -> None:
    refused = api.get(f"{BACKUPS}?{query}", headers=reader)
    assert refused.status_code == 422
    assert [(fault["pointer"], fault["code"]) for fault in refused.json()["fields"]] == [
        (pointer, code)
    ]


@pytest.mark.requirement("WF-IHM-0130-A")
@pytest.mark.usefixtures("backups")
def test_a_bound_beyond_the_integers_of_the_database_keeps_what_it_would(
    api: ContractClient, reader: dict[str, str]
) -> None:
    assert listed(api, reader, f"size_bytes_max={2**70}")[1]["total"] == 5
    assert listed(api, reader, f"size_bytes_min={2**70}")[0] == []
