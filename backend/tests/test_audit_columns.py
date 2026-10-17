# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The columns of audit of the tables of the accounts and of the roles, as the API gives them.

« Créé le », « Créé par », « Modifié le » and « Modifié par » are sorted and filtered as the other
columns of the two tables (WF-IHM-0060, WF-IHM-0130). The rows are written around the service
(``access_rows``) with the same columns of audit in both tables, so that one expectation holds for
each: the accounts Bernard, Petit and Roux, and the roles of the same names, besides the caller,
Camille Martin, and her role, « Martin », which the platform created. Their authors are Alix
Moreau, deactivated, an account anonymised, Camille Martin and the platform. The deactivated
authors are no rows of the table of the accounts read here, which keeps the active ones alone.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import insert, update
from support import ContractClient, bearer, raw_account

from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database

USERS = "/api/v1/users"
ROLES = "/api/v1/access-roles"
SUBJECT = "5e8a1c3f-2b7d-4f90-8a61-3c2e9d7b4f15"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
TABLES = [USERS, ROLES]
# The rows in the order of their creation, and of their last change.
BY_CREATION = ["Bernard", "Petit", "Roux", "Martin"]
BY_CHANGE = ["Petit", "Bernard", "Roux", "Martin"]


def instant(month: int, day: int = 1) -> datetime:
    """Give an instant of 2026, at midnight in universal time."""
    return datetime(2026, month, day, tzinfo=UTC)


def stamp(moment: datetime) -> str:
    """Write an instant as the query carries it."""
    return moment.isoformat().replace("+00:00", "Z")


def audit(
    created: datetime, created_by: UUID | None, updated: datetime, updated_by: UUID | None
) -> dict[str, Any]:
    """Give the columns of audit of a row: its dates and authors, ``None`` for the platform."""
    return {
        "created_at": created,
        "created_by": created_by,
        "updated_at": updated,
        "updated_by": updated_by,
    }


@pytest.fixture
def authors(database: Database) -> dict[str, UUID]:
    """Write the authors deactivated, Alix Moreau and an account anonymised; give them by name."""
    alix = account(database, "Moreau", "Alix", state="deactivated")
    anonymised = raw_account(
        last_name=None,
        first_name=None,
        email=None,
        anonymized_at=instant(5),
        state="deactivated",
    )
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**anonymised))
    return {"Alix Moreau": alix, "anonymised": UUID(str(anonymised["id"]))}


@pytest.fixture
def rows(database: Database, realm: TestRealm, authors: dict[str, UUID]) -> dict[str, str]:
    """Write the caller and the rows of both tables; give the header of the caller's token.

    Camille Martin and her role, « Martin », by the platform on 1 October 2026; Bernard, created
    by the platform, changed by Alix Moreau; Petit, created by Alix Moreau, changed by the account
    anonymised; Roux, created by Camille Martin, changed by the platform.
    """
    alix, anonymised = authors["Alix Moreau"], authors["anonymised"]
    held = role(database, "Martin", permissions=("users.read", "access_roles.read"))
    account(database, "Martin", "Camille", roles=(held,), id=CALLER, idp_subject=SUBJECT)
    written = {
        "Bernard": audit(instant(1), None, instant(3), alix),
        "Petit": audit(instant(2), alix, instant(2, 15), anonymised),
        "Roux": audit(instant(3), CALLER, instant(4), None),
    }
    for name, columns in written.items():
        account(database, name, "Test", **columns)
        identifier = role(database, name)
        with database.transaction() as session:
            session.execute(update(AccessRole).where(AccessRole.id == identifier).values(**columns))
    return bearer(realm.token(SUBJECT, KEY))


def read(api: ContractClient, headers: dict[str, str], table: str, query: str) -> list[Any]:
    """Read a table for a query, each row as the contract gives it."""
    response = api.get(f"{table}{query}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    return body["items"] if table == USERS else body


def named(api: ContractClient, headers: dict[str, str], table: str, query: str = "") -> list[str]:
    """Give the rows of a table in its order, an account by its name, a role by its label."""
    key = "last_name" if table == USERS else "label"
    return [row[key] for row in read(api, headers, table, query)]


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize(
    ("column", "orders"),
    [
        ("created_at", (BY_CREATION, BY_CREATION[::-1])),
        ("updated_at", (BY_CHANGE, BY_CHANGE[::-1])),
        # By the displayed name, the first name then the name: Alix Moreau before Camille Martin,
        # though Martin comes before Moreau; the platform after the accounts, ascending; equals in
        # the order of the table unsorted, whatever the direction.
        (
            "created_by",
            (["Petit", "Roux", "Bernard", "Martin"], ["Bernard", "Martin", "Roux", "Petit"]),
        ),
        # An account anonymised, which has no name, after the names and before the platform.
        (
            "updated_by",
            (["Bernard", "Petit", "Martin", "Roux"], ["Martin", "Roux", "Petit", "Bernard"]),
        ),
    ],
)
@pytest.mark.requirement("WF-IHM-0060-A")
def test_each_column_of_audit_of_the_two_tables_is_sorted_both_ways(
    api: ContractClient,
    rows: dict[str, str],
    table: str,
    column: str,
    orders: tuple[list[str], list[str]],
) -> None:
    # « Chaque colonne d'une table plate se trie dans les deux sens. »
    ascending, descending = orders
    assert named(api, rows, table, f"?sort_by={column}") == ascending
    assert named(api, rows, table, f"?sort_by={column}&sort_order=desc") == descending


def test_the_pages_of_accounts_equal_on_an_author_neither_repeat_nor_skip_one(
    api: ContractClient, database: Database, rows: dict[str, str]
) -> None:
    # Criterion of US-0360: at equal values, the order is the same from a page to the next; twins
    # created by the platform come by identifier.
    twins = sorted(
        str(account(database, "Durand", "Léa", email=f"{uuid4().hex}@example.org"))
        for _ in range(3)
    )
    for direction in ("asc", "desc"):
        query = f"?sort_by=created_by&sort_order={direction}&created_by_kind=platform&limit=2"
        pages = [read_page(api, rows, f"{query}&offset={offset}") for offset in (0, 2, 4)]
        in_turn = [each["user_id"] for page in pages for each in page]
        assert [user_id for user_id in in_turn if user_id in twins] == twins
        assert len(in_turn) == len(set(in_turn)) == 5


def read_page(api: ContractClient, headers: dict[str, str], query: str) -> list[Any]:
    """Read a page of the table of the accounts."""
    return read(api, headers, USERS, query)


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize(
    ("query", "kept"),
    [
        ("?created_by_kind=platform", ["Bernard", "Martin"]),
        ("?created_by_kind=user", ["Petit", "Roux"]),
        ("?updated_by_kind=user", ["Bernard", "Petit"]),
        ("?updated_by_kind=platform", ["Martin", "Roux"]),
        (f"?created_by_user_id={CALLER}", ["Roux"]),
        (f"?created_by_user_id={CALLER}&created_by_kind=platform", []),
        (f"?updated_by_user_id={uuid4()}", []),
        # A period, its start included, its end excluded.
        (f"?created_at_from={stamp(instant(2))}&created_at_to={stamp(instant(3))}", ["Petit"]),
        (f"?created_at_from={stamp(instant(3))}", ["Martin", "Roux"]),
        (f"?updated_at_to={stamp(instant(3))}", ["Petit"]),
        (f"?updated_at_from={stamp(instant(3))}", ["Bernard", "Martin", "Roux"]),
        # An instant in another offset is the same instant.
        (
            (
                "?updated_at_from=2026-03-01T01:00:00%2B01:00"
                "&updated_at_to=2026-03-01T02:00:00%2B01:00"
            ),
            ["Bernard"],
        ),
        # A period whose end is its start is empty.
        (f"?created_at_from={stamp(instant(3))}&created_at_to={stamp(instant(3))}", []),
        # The filters combine, with each other and with the sort.
        (
            (
                f"?created_by_kind=user&updated_at_from={stamp(instant(2, 15))}"
                "&sort_by=updated_at&sort_order=desc"
            ),
            ["Roux", "Petit"],
        ),
    ],
)
def test_each_column_of_audit_of_the_two_tables_is_filtered(
    api: ContractClient, rows: dict[str, str], table: str, query: str, kept: list[str]
) -> None:
    # Criterion of US-0360, filters: each column, combined with the others and with the sort; the
    # total of the accounts is that of the accounts the filters keep (WF-IHM-0130).
    assert named(api, rows, table, query) == kept
    if table == USERS:
        response = api.get(f"{USERS}{query}", headers=rows)
        assert response.json()["meta"]["total"] == len(kept)


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.requirement("WF-ADM-0060-A")
def test_a_deactivated_author_stays_named_and_an_anonymised_one_is_said_by_no_name(
    api: ContractClient, rows: dict[str, str], authors: dict[str, UUID], table: str
) -> None:
    # Écart : « Une révision marquée par un compte depuis désactivé affiche toujours son auteur. »
    # Here, a deactivated account stays named in the columns of audit of the accounts and of the
    # roles it wrote; anonymised, it has no name there, the front showing the neutral label of its
    # catalogue, while its acts stay its own (« Après anonymisation d'un compte désactivé, aucun
    # écran […] ne présente plus son nom ni son adresse »).
    key = "last_name" if table == USERS else "label"
    found = {row[key]: row["audit"] for row in read(api, rows, table, "?sort_by=created_at")}
    alix = {"kind": "user", "user_id": str(authors["Alix Moreau"]), "display_name": "Alix Moreau"}
    assert found["Bernard"]["updated_by"] == alix
    assert found["Petit"]["created_by"] == alix
    assert found["Petit"]["updated_by"] == {
        "kind": "user",
        "user_id": str(authors["anonymised"]),
        "display_name": None,
    }
    assert found["Bernard"]["created_by"] == {"kind": "platform"}
    assert found["Roux"]["created_by"]["display_name"] == "Camille Martin"
    # Filtered on them, the rows they wrote are kept, deactivated or anonymised as they are.
    by_alix = f"?created_by_user_id={authors['Alix Moreau']}"
    assert named(api, rows, table, by_alix) == ["Petit"]
    assert named(api, rows, table, f"?updated_by_user_id={authors['anonymised']}") == ["Petit"]


def refused(name: str, code: str = "VALIDATION_FAILED") -> list[dict[str, Any]]:
    """Give the one field a refusal names: a parameter of the query, by its code."""
    return [{"pointer": f"/query/{name}", "code": code}]


def problem(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


def as_expected(given: list[dict[str, Any]], fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give the fields of a refusal by the keys each expected one names, one for one, in order."""
    pairs = zip(given, fields, strict=True)
    return [{key: field[key] for key in expected} for field, expected in pairs]


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            f"?created_at_from={stamp(instant(3))}&created_at_to={stamp(instant(1))}",
            [
                {
                    "pointer": "/query/created_at_to",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": "2026-03-01T00:00:00Z"},
                }
            ],
        ),
        # Both periods inverted, both ends named; the start in universal time.
        (
            (
                "?created_at_from=2026-03-01T01:00:00%2B01:00&created_at_to=2026-01-01T00:00:00Z"
                f"&updated_at_from={stamp(instant(6))}&updated_at_to={stamp(instant(5))}"
            ),
            [
                {
                    "pointer": "/query/created_at_to",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": "2026-03-01T00:00:00Z"},
                },
                {
                    "pointer": "/query/updated_at_to",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": "2026-06-01T00:00:00Z"},
                },
            ],
        ),
        # An instant malformed, or without its offset.
        ("?created_at_from=yesterday", refused("created_at_from", "DATE_INVALID")),
        ("?updated_at_to=2026-03-01T00:00:00", refused("updated_at_to", "DATE_INVALID")),
        ("?created_by_kind=robot", refused("created_by_kind")),
        ("?updated_by_user_id=nope", refused("updated_by_user_id")),
        ("?sort_by=created", refused("sort_by")),
    ],
)
def test_a_filter_of_the_columns_of_audit_the_tables_refuse_is_named(
    api: ContractClient,
    rows: dict[str, str],
    table: str,
    query: str,
    fields: list[dict[str, Any]],
) -> None:
    # The rule of every period of the contract (README, « Une période… »), the end of an inverted
    # one named, the start given; a value outside the schema of a parameter refused at its field.
    status, code, given = problem(api.get(f"{table}{query}", headers=rows))
    assert (status, code) == (422, "VALIDATION_FAILED")
    assert as_expected(given, fields) == fields


# A period of creation inverted, and the fault the contract gives it.
INVERTED = f"created_at_from={stamp(instant(3))}&created_at_to={stamp(instant(1))}"
INVERTED_FAULT = {
    "pointer": "/query/created_at_to",
    "code": "VALUE_OUT_OF_RANGE",
    "params": {"minimum": "2026-03-01T00:00:00Z"},
}


def test_an_account_query_with_an_unknown_origin_and_an_inverted_period_names_both(
    api: ContractClient, rows: dict[str, str]
) -> None:
    # A query that commits several faults sees each named, those of the table with those of its
    # columns of audit, in one refusal.
    query = f"?origins=local,elsewhere&{INVERTED}"
    status, code, given = problem(api.get(f"{USERS}{query}", headers=rows))
    assert (status, code) == (422, "VALIDATION_FAILED")
    fields = [{"pointer": "/query/origins", "code": "VALIDATION_FAILED"}, INVERTED_FAULT]
    assert as_expected(given, fields) == fields


def test_a_role_query_with_inverted_bounds_and_an_inverted_period_names_both(
    api: ContractClient, rows: dict[str, str]
) -> None:
    # The same for the roles: the upper bound under the lower one, and the period of creation.
    query = f"?holder_count_min=2&holder_count_max=1&{INVERTED}"
    status, code, given = problem(api.get(f"{ROLES}{query}", headers=rows))
    assert (status, code) == (422, "VALIDATION_FAILED")
    bounds = {"pointer": "/query/holder_count_max", "code": "VALUE_OUT_OF_RANGE"}
    fields = [{**bounds, "params": {"minimum": 2}}, INVERTED_FAULT]
    assert as_expected(given, fields) == fields
