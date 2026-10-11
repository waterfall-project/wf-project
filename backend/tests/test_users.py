# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the accounts and an account, as the API gives them (US-0360).

The accounts and their roles are written around the service (``access_rows``) and read through the
API, whose every answer is checked against the contract (``ContractClient``). The caller, Camille
Martin, is one of the accounts: she holds a role of her own, « Accès aux comptes », which gives her
the permissions a test asks for (``caller_permissions``) — to consult the accounts, unless it says
otherwise.
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import ADMINISTRATION, role
from openapi_core.templating.responses.exceptions import ResponseNotFound
from realm import KEY, TestRealm
from sqlalchemy import insert
from support import ContractClient, bearer, raw_account

from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import Database

USERS = "/api/v1/users"
SUBJECT = "4b7c1d2e-8f3a-4c6b-9e1d-2a5f7c9b0e13"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
CONSULT = "users.read"


def account(
    database: Database,
    last_name: str,
    first_name: str,
    *,
    roles: tuple[UUID, ...] = (),
    **columns: object,
) -> UUID:
    """Write an account around the service, with the roles it holds; give its identifier."""
    email = f"{first_name}.{last_name}@example.org".lower().replace(" ", "")
    row = raw_account(
        **{"last_name": last_name, "first_name": first_name, "email": email, **columns}
    )
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
        for held in roles:
            session.execute(
                insert(UserAccessRole).values(user_account_id=row["id"], access_role_id=held)
            )
    return UUID(str(row["id"]))


@pytest.fixture
def caller_permissions() -> tuple[str, ...]:
    """Give the permissions the role of the caller grants: to consult the accounts."""
    return (CONSULT,)


@pytest.fixture
def headers(
    database: Database, realm: TestRealm, caller_permissions: tuple[str, ...]
) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and her role; give her token's header."""
    held = role(database, "Accès aux comptes", permissions=caller_permissions)
    account(
        database,
        "Martin",
        "Camille",
        roles=(held,),
        id=CALLER,
        idp_subject=SUBJECT,
        email="camille.martin@example.org",
    )
    return bearer(realm.token(SUBJECT, KEY))


@pytest.fixture
def table(database: Database, headers: dict[str, str]) -> dict[str, UUID]:
    """Write accounts whose orders differ on each column, beside the caller; give them by name."""
    del headers
    manager, chief = role(database, "Manager"), role(database, "Chef de projet")
    estimator, pilot = role(database, "Chiffreur"), role(database, "Pilote")
    return {
        "Bernard Dominique": account(
            database, "Bernard", "Dominique", origin="directory", roles=(manager,)
        ),
        "Lefèvre Sacha": account(database, "Lefèvre", "Sacha", origin="identity_provider"),
        "Martin Bastien": account(database, "Martin", "Bastien", roles=(estimator,)),
        "Moreau Alix": account(database, "Moreau", "Alix", state="deactivated", roles=(chief,)),
        # An address in capitals sorts before those in small letters, in the code points.
        "Petit Lucas": account(
            database, "Petit", "Lucas", email="Lucas.Petit@example.org", roles=(estimator,)
        ),
        # Her roles are held by label: « Chiffreur », then « Pilote ».
        "Roux Inès": account(database, "Roux", "Inès", roles=(pilot, estimator)),
        "de Vries Anna": account(database, "de Vries", "Anna", origin="directory"),
        "Émery Zoé": account(database, "Émery", "Zoé"),
    }


def read(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the table of the accounts for a query of filters, sort and page."""
    response = api.get(f"{USERS}{query}", headers=headers)
    assert response.status_code == 200
    return response.json()


def names(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the accounts of a page of the table, in its order, by name and first name."""
    return [
        f"{each['last_name']} {each['first_name']}" for each in read(api, headers, query)["items"]
    ]


# Every account, the deactivated one included, in the order of the table unsorted: by name, then
# first name, in the order of the code points — capitals, small letters, then accented capitals.
EVERY_ONE = [
    "Bernard Dominique",
    "Lefèvre Sacha",
    "Martin Bastien",
    "Martin Camille",
    "Moreau Alix",
    "Petit Lucas",
    "Roux Inès",
    "de Vries Anna",
    "Émery Zoé",
]
ALL = "?include_inactive=true"


def test_the_table_gives_each_account_with_its_columns_and_its_roles_named(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # Criterion of US-0360: each account with its name, first name, address, origin, attachment,
    # roles named by the server and state (WF-ADM-0050).
    items = {each["user_id"]: each for each in read(api, headers, ALL)["items"]}
    ines = items[str(table["Roux Inès"])]
    assert {name: ines[name] for name in ("email", "origin", "is_active", "org_node_label")} == {
        "email": "inès.roux@example.org",
        "origin": "local",
        "is_active": True,
        "org_node_label": None,
    }
    assert ines["access_role_labels"] == ["Chiffreur", "Pilote"]
    assert len(ines["access_role_ids"]) == 2
    assert items[str(table["Moreau Alix"])]["is_active"] is False
    assert items[str(table["Lefèvre Sacha"])]["access_role_ids"] == []


def test_the_table_keeps_the_active_accounts_unless_the_deactivated_are_asked_for(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    assert set(table) <= set(EVERY_ONE)
    assert names(api, headers) == [name for name in EVERY_ONE if name != "Moreau Alix"]
    assert names(api, headers, ALL) == EVERY_ONE


@pytest.mark.parametrize(
    ("column", "ascending"),
    [
        ("last_name", EVERY_ONE),
        (
            "first_name",
            [
                "Moreau Alix",
                "de Vries Anna",
                "Martin Bastien",
                "Martin Camille",
                "Bernard Dominique",
                "Roux Inès",
                "Petit Lucas",
                "Lefèvre Sacha",
                "Émery Zoé",
            ],
        ),
        (
            "email",
            [
                "Petit Lucas",
                "Moreau Alix",
                "de Vries Anna",
                "Martin Bastien",
                "Martin Camille",
                "Bernard Dominique",
                "Roux Inès",
                "Lefèvre Sacha",
                "Émery Zoé",
            ],
        ),
    ],
)
@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_accounts_are_sorted_on_a_text_in_the_order_of_the_code_points_both_ways(
    api: ContractClient,
    headers: dict[str, str],
    table: dict[str, UUID],
    column: str,
    ascending: list[str],
) -> None:
    # « Chaque colonne d'une table plate se trie dans les deux sens. »
    assert set(table) <= set(ascending)
    assert names(api, headers, f"{ALL}&sort_by={column}") == ascending
    descending = names(api, headers, f"{ALL}&sort_by={column}&sort_order=desc")
    if column == "last_name":
        # The two Martin are equal on the name: by first name, ascending in both directions.
        assert descending == [
            "Émery Zoé",
            "de Vries Anna",
            "Roux Inès",
            "Petit Lucas",
            "Moreau Alix",
            "Martin Bastien",
            "Martin Camille",
            "Lefèvre Sacha",
            "Bernard Dominique",
        ]
    else:
        assert descending == ascending[::-1]


@pytest.mark.parametrize(
    ("column", "groups"),
    [
        # The origins in the order of their enumeration, each group by name.
        (
            "origin",
            [
                [
                    "Martin Bastien",
                    "Martin Camille",
                    "Moreau Alix",
                    "Petit Lucas",
                    "Roux Inès",
                    "Émery Zoé",
                ],
                ["Bernard Dominique", "de Vries Anna"],
                ["Lefèvre Sacha"],
            ],
        ),
        # The roles by their labels in the order the account holds them; none before any.
        (
            "access_roles",
            [
                ["Lefèvre Sacha", "de Vries Anna", "Émery Zoé"],
                ["Martin Camille"],
                ["Moreau Alix"],
                ["Martin Bastien", "Petit Lucas"],
                ["Roux Inès"],
                ["Bernard Dominique"],
            ],
        ),
        # The deactivated accounts after the active ones.
        ("is_active", [[name for name in EVERY_ONE if name != "Moreau Alix"], ["Moreau Alix"]]),
        # No account is attached to a node before EP-05: all equal, by name.
        ("org_node", [EVERY_ONE]),
    ],
)
@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_accounts_are_sorted_on_each_other_column_both_ways_equals_by_name(
    api: ContractClient,
    headers: dict[str, str],
    table: dict[str, UUID],
    column: str,
    groups: list[list[str]],
) -> None:
    # « Chaque colonne d'une table plate se trie dans les deux sens. » Equals keep the order of
    # the table unsorted, whatever the direction.
    assert set(table) <= {name for group in groups for name in group}
    assert names(api, headers, f"{ALL}&sort_by={column}") == [n for g in groups for n in g]
    assert names(api, headers, f"{ALL}&sort_by={column}&sort_order=desc") == [
        n for g in reversed(groups) for n in g
    ]


@pytest.mark.requirement("WF-IHM-0060-A")
@pytest.mark.parametrize("column", ["last_name", "origin", "access_roles", "is_active"])
def test_the_pages_of_accounts_equal_on_the_sort_neither_repeat_nor_skip_one(
    api: ContractClient, database: Database, headers: dict[str, str], column: str
) -> None:
    # Criterion of US-0360: at equal values, the order is the same from a page to the next; the
    # identifier ends every tie, ascending, as the name and the first name of twins are equal.
    twins = [
        str(twin)
        for twin in sorted(
            account(database, "Durand", "Léa", email=f"{uuid4().hex}@example.org") for _ in range(5)
        )
    ]
    for direction in ("asc", "desc"):
        query = f"?sort_by={column}&sort_order={direction}&limit=2"
        pages = [read(api, headers, f"{query}&offset={offset}") for offset in range(0, 6, 2)]
        assert [page["meta"]["total"] for page in pages] == [6, 6, 6]
        in_turn = [each["user_id"] for page in pages for each in page["items"]]
        assert len(in_turn) == 6
        assert set(in_turn) == {str(CALLER), *twins}
        assert [user_id for user_id in in_turn if user_id != str(CALLER)] == twins


def test_the_table_is_read_by_pages_of_fifty_and_says_the_total(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # Criterion of US-0360, pagination: pages of fifty by default, the total announced, the page
    # read; a page beyond the last one is empty and announces the same total.
    for number in range(54):
        account(database, f"Compte {number:02}", "Test")
    first = read(api, headers)
    assert first["meta"] == {"limit": 50, "offset": 0, "total": 55}
    assert len(first["items"]) == 50
    second = read(api, headers, "?offset=50")
    assert second["meta"] == {"limit": 50, "offset": 50, "total": 55}
    every = [each["user_id"] for each in first["items"] + second["items"]]
    assert len(set(every)) == 55
    beyond = read(api, headers, "?offset=500&limit=10")
    assert beyond == {"items": [], "meta": {"limit": 10, "offset": 500, "total": 55}}


@pytest.mark.parametrize(
    ("query", "kept"),
    [
        # The search ignores case and accents, on the name, the first name, the address, and the
        # first name followed by the name, which no column holds whole.
        ("?search=ROUX", ["Roux Inès"]),
        ("?search=ines", ["Roux Inès"]),
        ("?search=ines%20roux", ["Roux Inès"]),
        ("?search=emery", ["Émery Zoé"]),
        ("?search=lucas.petit%40", ["Petit Lucas"]),
        ("?search=martin", ["Martin Bastien", "Martin Camille"]),
        ("?search=%25", []),
        (
            "?origins=directory,identity_provider",
            ["Bernard Dominique", "Lefèvre Sacha", "de Vries Anna"],
        ),
        ("?is_active=false", ["Moreau Alix"]),
        ("?is_active=true&include_inactive=true", [n for n in EVERY_ONE if n != "Moreau Alix"]),
        # No account is attached to a node before EP-05.
        (f"?org_node_id={uuid4()}", []),
        # The filters combine, and combine with the sort; the deactivated join on demand.
        ("?search=martin&sort_by=first_name&sort_order=desc", ["Martin Camille", "Martin Bastien"]),
        ("?search=al", []),
        ("?search=al&include_inactive=true", ["Moreau Alix"]),
        (
            "?origins=local&include_inactive=true&sort_by=is_active&sort_order=desc",
            [
                "Moreau Alix",
                "Martin Bastien",
                "Martin Camille",
                "Petit Lucas",
                "Roux Inès",
                "Émery Zoé",
            ],
        ),
    ],
)
def test_the_table_of_the_accounts_is_filtered_on_each_of_its_columns(
    api: ContractClient,
    headers: dict[str, str],
    table: dict[str, UUID],
    query: str,
    kept: list[str],
) -> None:
    # Criterion of US-0360, filters: each column, combined with each other and with the sort; the
    # total is that of the accounts the filters keep.
    assert set(table) | {"Martin Camille"} >= set(kept)
    assert names(api, headers, query) == kept
    assert read(api, headers, query)["meta"]["total"] == len(kept)


def test_the_accounts_are_filtered_on_the_roles_they_hold(
    api: ContractClient, database: Database, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    held = {label: role(database, label) for label in ("Gestion", "Audit")}
    account(database, "Garnier", "Hugo", roles=(held["Gestion"],))
    account(database, "Henry", "Maël", roles=(held["Gestion"], held["Audit"]))
    deleted = role(database, "Ancien", deleted=True)
    ids = ",".join(str(held[label]) for label in ("Gestion", "Audit"))
    assert names(api, headers, f"?access_role_ids={ids}") == ["Garnier Hugo", "Henry Maël"]
    assert names(api, headers, f"?access_role_ids={held['Audit']}") == ["Henry Maël"]
    # A role that does not exist, or no longer, keeps no account.
    assert names(api, headers, f"?access_role_ids={uuid4()},{deleted}") == []
    assert set(table).isdisjoint(names(api, headers, f"?access_role_ids={ids}"))


def problem(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


@pytest.mark.xfail(raises=ResponseNotFound, strict=True, reason="#799")
@pytest.mark.parametrize(
    ("query", "pointer"),
    [
        ("?limit=0", "/query/limit"),
        ("?offset=-1", "/query/offset"),
        ("?sort_by=state", "/query/sort_by"),
        ("?search=%00", "/query/search"),
        ("?origins=local,ldap", "/query/origins"),
        ("?origins=", "/query/origins"),
        ("?access_role_ids=nope", "/query/access_role_ids"),
        ("?org_node_id=nope", "/query/org_node_id"),
    ],
)
def test_a_parameter_the_table_refuses_is_a_value_refused(
    api: ContractClient, headers: dict[str, str], query: str, pointer: str
) -> None:
    # A value outside the schema of a parameter is refused at its field (422), never a 500; the
    # contract does not declare the 422 of listUsers yet (#799).
    response = api.get(f"{USERS}{query}", headers=headers)
    status, code, fields = problem(response)
    assert (status, code, [field["pointer"] for field in fields]) == (
        422,
        "VALIDATION_FAILED",
        [pointer],
    )


@pytest.mark.parametrize("path", [USERS, f"{USERS}/{uuid4()}"])
def test_the_accounts_are_read_by_a_known_caller_only(api: ContractClient, path: str) -> None:
    assert problem(api.get(path))[:2] == (401, "SESSION_REQUIRED")


def test_an_account_is_read_with_its_roles_named_in_the_order_it_holds_them(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    response = api.get(f"{USERS}/{table['Roux Inès']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert (body["last_name"], body["first_name"]) == ("Roux", "Inès")
    assert body["access_role_labels"] == ["Chiffreur", "Pilote"]
    assert body["audit"]["created_by"] == {"kind": "platform"}
    # A reader who may not change the accounts is offered no command.
    assert body["available_commands"] == []
    deactivated = api.get(f"{USERS}/{table['Moreau Alix']}", headers=headers)
    assert deactivated.json()["is_active"] is False


@pytest.mark.requirement("WF-ADM-0110-A")
def test_an_unknown_account_and_an_account_not_consultable_get_the_same_answer(
    api: ContractClient, database: Database, realm: TestRealm, headers: dict[str, str]
) -> None:
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » : constated for an account (#753), as US-0390 does for a role.
    subject = f"subject-{uuid4()}"
    without = role(database, "Écriture seule", permissions=("users.write", "estimate.read"))
    account(database, "Blanc", "Rémi", idp_subject=subject, roles=(without,))
    may_not = bearer(realm.token(subject, KEY))
    unknown = api.get(f"{USERS}/{uuid4()}", headers=headers)
    not_consultable = api.get(f"{USERS}/{CALLER}", headers=may_not)
    assert unknown.status_code == not_consultable.status_code == 404
    assert unknown.headers["content-type"] == not_consultable.headers["content-type"]
    bodies = [answer.json() for answer in (unknown, not_consultable)]
    assert [body.pop("correlation_id") for body in bodies] == [
        unknown.headers[HEADER],
        not_consultable.headers[HEADER],
    ]
    assert bodies[0] == bodies[1] == {"code": "NOT_FOUND", "status": 404}
    # The table does not exist for it either.
    assert problem(api.get(USERS, headers=may_not))[:2] == (404, "NOT_FOUND")


def commands(api: ContractClient, headers: dict[str, str], user_id: UUID) -> list[dict[str, Any]]:
    """Give the commands an account carries for the caller."""
    response = api.get(f"{USERS}/{user_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["available_commands"]


def available(command: str, *missing: str) -> dict[str, Any]:
    """Describe a command as the contract does: available unless a condition is missing."""
    return {"command": command, "is_available": not missing, "missing_conditions": list(missing)}


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
def test_an_account_carries_the_commands_its_reader_may_exercise(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # WF-IHM-0090: the one that changes the state, then the attribution of the roles.
    assert commands(api, headers, table["Roux Inès"]) == [
        available("deactivate"),
        available("set_access_roles"),
    ]
    assert commands(api, headers, table["Moreau Alix"]) == [
        available("reactivate"),
        available("set_access_roles"),
    ]
    # The caller is the only active account that holds the administration: its deactivation is
    # unavailable, the attribution of its roles is not (WF-ADM-0120).
    alone = [available("deactivate", "last_administrator"), available("set_access_roles")]
    assert commands(api, headers, CALLER) == alone
    listed = read(api, headers, "?search=camille")["items"]
    assert [each["available_commands"] for each in listed] == [alone]


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
def test_the_deactivation_of_an_administrator_is_available_once_another_holds_the_administration(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    second = role(database, "Administration", permissions=ADMINISTRATION)
    account(database, "Noir", "Jade", roles=(second,))
    # A deactivated holder does not count: the administration is held by an active account.
    account(database, "Gris", "Tom", state="deactivated", roles=(second,))
    assert commands(api, headers, CALLER)[0] == available("deactivate")
