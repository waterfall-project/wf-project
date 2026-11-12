# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the accounts and an account, as the API gives them (US-0360).

The accounts and their roles are written around the service (``access_rows``) and read through the
API, whose every answer is checked against the contract (``ContractClient``). The caller, Camille
Martin, is one of the accounts: she holds a role of her own, « Accès aux comptes », which gives her
the permissions a test asks for (``caller_permissions``) — to consult the accounts, unless it says
otherwise.
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import ADMINISTRATION, account, anonymized_account, role
from realm import KEY, TestRealm
from support import ContractClient, bearer

from waterfall.core.users.interface import (
    Identity,
    create_local_account,
    read_installation_administrator,
)
from waterfall.platform.audit import Act
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from waterfall.platform.database import Database

USERS = "/api/v1/users"
# An identifier no row holds, fixed: the identifiers of the tests are the same in each process
# that collects them (pytest-xdist).
UNKNOWN = UUID("7d1e5b0a-3c94-4f2e-9a68-5b20c4e1f9d3")
SUBJECT = "4b7c1d2e-8f3a-4c6b-9e1d-2a5f7c9b0e13"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
CONSULT = "users.read"


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
    # A label in an accented capital comes after any other in the code points, not among the E.
    team = role(database, "Équipe")
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
        "de Vries Anna": account(database, "de Vries", "Anna", origin="directory", roles=(team,)),
        "Émery Élise": account(database, "Émery", "Élise"),
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
    "Émery Élise",
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
        # Élise, in an accented capital, after every other, where a language puts her among the E.
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
                "Émery Élise",
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
                "Émery Élise",
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
            "Émery Élise",
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
                    "Émery Élise",
                ],
                ["Bernard Dominique", "de Vries Anna"],
                ["Lefèvre Sacha"],
            ],
        ),
        # The roles by their labels in the order the account holds them, compared in the order of
        # the code points; an account without a role, a cell without a value, after the others.
        (
            "access_roles",
            [
                ["Martin Camille"],
                ["Moreau Alix"],
                ["Martin Bastien", "Petit Lucas"],
                ["Roux Inès"],
                ["Bernard Dominique"],
                ["de Vries Anna"],
                ["Lefèvre Sacha", "Émery Élise"],
            ],
        ),
        # The deactivated accounts after the active ones.
        ("is_active", [[name for name in EVERY_ONE if name != "Moreau Alix"], ["Moreau Alix"]]),
        # No account of this table is attached to a node: all equal, by name.
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
        ("?search=emery", ["Émery Élise"]),
        ("?search=lucas.petit%40", ["Petit Lucas"]),
        ("?search=martin", ["Martin Bastien", "Martin Camille"]),
        ("?search=%25", []),
        (
            "?origins=directory,identity_provider",
            ["Bernard Dominique", "Lefèvre Sacha", "de Vries Anna"],
        ),
        ("?is_active=false", ["Moreau Alix"]),
        ("?is_active=true&include_inactive=true", [n for n in EVERY_ONE if n != "Moreau Alix"]),
        # A node no account is attached to, nor any of its descendants, keeps none.
        (f"?org_node_id={UNKNOWN}", []),
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
                "Émery Élise",
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


@pytest.fixture
def roleless(database: Database, table: dict[str, UUID]) -> UUID:
    """Write accounts beside the table; give the identifier of the role « Gestion ».

    A holder of « Gestion », an account whose only role was deleted, and a deactivated account
    without a role.
    """
    del table
    managing = role(database, "Gestion")
    account(database, "Garnier", "Hugo", roles=(managing,))
    account(database, "Nadal", "Zoé", roles=(role(database, "Ancien", deleted=True),))
    account(database, "Olivier", "Paul", state="deactivated")
    return managing


# The active accounts without a role, in the order of the table unsorted: Sacha Lefèvre, whom the
# identity provider created, Zoé Nadal, whose only role was deleted, and Élise Émery.
WITHOUT_ROLE = ["Lefèvre Sacha", "Nadal Zoé", "Émery Élise"]
WITHOUT = "?without_access_role=true"


@pytest.mark.requirement("WF-ADM-0180-A")
def test_the_accounts_without_a_role_are_retained_alone_or_with_the_roles_asked(
    api: ContractClient, headers: dict[str, str], roleless: UUID
) -> None:
    # « Avec un fournisseur externe, la première connexion d'une personne inconnue crée son
    # compte, sans rôle » : the table retains them by a parameter, the screen offering « Sans
    # rôle » among the roles (US-1860, #2976). A deleted role is held no more.
    page = read(api, headers, WITHOUT)
    assert [f"{each['last_name']} {each['first_name']}" for each in page["items"]] == WITHOUT_ROLE
    assert all(each["access_role_ids"] == [] for each in page["items"])
    assert page["meta"]["total"] == len(WITHOUT_ROLE)
    # With the roles asked, their union: the holders of « Gestion » are added to them.
    union = f"{WITHOUT}&access_role_ids={roleless}"
    assert names(api, headers, union) == ["Garnier Hugo", *WITHOUT_ROLE]
    assert names(api, headers, f"?access_role_ids={roleless},{uuid4()}&{WITHOUT[1:]}") == [
        "Garnier Hugo",
        *WITHOUT_ROLE,
    ]
    # Absent or false, nothing changes.
    assert names(api, headers, "?without_access_role=false") == names(api, headers)
    assert "Lefèvre Sacha" in names(api, headers)
    only_held = f"?access_role_ids={roleless}"
    assert names(api, headers, f"{only_held}&without_access_role=false") == ["Garnier Hugo"]
    assert names(api, headers, only_held) == ["Garnier Hugo"]


@pytest.mark.requirement("WF-ADM-0180-A")
@pytest.mark.parametrize(
    ("query", "kept", "total"),
    [
        # « Créé par le fournisseur d'identité » and « Sans rôle »: the newcomers to welcome.
        (f"{WITHOUT}&origins=identity_provider", ["Lefèvre Sacha"], 1),
        (f"{WITHOUT}&origins=local,directory", ["Nadal Zoé", "Émery Élise"], 2),
        (f"{WITHOUT}&search=zoé", ["Nadal Zoé"], 1),
        (f"{WITHOUT}&include_inactive=true", [*WITHOUT_ROLE[:2], "Olivier Paul", "Émery Élise"], 4),
        (f"{WITHOUT}&is_active=false", ["Olivier Paul"], 1),
        (f"{WITHOUT}&sort_by=last_name&sort_order=desc", WITHOUT_ROLE[::-1], 3),
        (f"{WITHOUT}&limit=2", WITHOUT_ROLE[:2], 3),
        (f"{WITHOUT}&limit=2&offset=2", WITHOUT_ROLE[2:], 3),
        (f"{WITHOUT}&limit=2&offset=4", [], 3),
    ],
)
@pytest.mark.usefixtures("roleless")
def test_the_accounts_without_a_role_combine_with_the_other_filters_and_the_pages(
    api: ContractClient, headers: dict[str, str], query: str, kept: list[str], total: int
) -> None:
    page = read(api, headers, query)
    assert [f"{each['last_name']} {each['first_name']}" for each in page["items"]] == kept
    assert page["meta"]["total"] == total


def problem(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


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
        ("?without_access_role=perhaps", "/query/without_access_role"),
        ("?org_node_id=nope", "/query/org_node_id"),
    ],
)
def test_a_parameter_the_table_refuses_is_a_value_refused(
    api: ContractClient, headers: dict[str, str], query: str, pointer: str
) -> None:
    # A value outside the schema of a parameter is refused at its field (422), never a 500, and
    # the contract declares that 422 (#799): the answer is read through it.
    status, code, fields = problem(api.get(f"{USERS}{query}", headers=headers))
    assert (status, code, [field["pointer"] for field in fields]) == (
        422,
        "VALIDATION_FAILED",
        [pointer],
    )


@pytest.mark.parametrize("path", [USERS, f"{USERS}/{UNKNOWN}"])
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


LINK = (available("create_password_link"), available("resend_invitation"))
DEACTIVATED_LINK = (
    available("create_password_link", "is_active_account"),
    available("resend_invitation", "is_active_account"),
)
LINK_COMMANDS = ("create_password_link", "resend_invitation")


def link_commands(listed: list[dict[str, Any]]) -> list[str]:
    """Give the commands of the link and of the invitation an account lists, in its order."""
    return [each["command"] for each in listed if each["command"] in LINK_COMMANDS]


@pytest.mark.parametrize("caller_permissions", [(CONSULT, "users.write")])
@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_local_account_lists_its_link_and_its_invitation_for_users_write_alone(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # « Le lien de fixation est le seul élément d'authentification qu'il présente » : the account
    # says its link and its invitation, available while it is active. They come from
    # ``users.write`` alone: this caller may not attribute the roles, and has them all the same.
    assert commands(api, headers, table["Roux Inès"]) == [available("deactivate"), *LINK]


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
@pytest.mark.requirement("WF-IHM-0090-A")
def test_the_link_and_the_invitation_of_a_deactivated_local_account_are_unavailable(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # « la commande [...] est présentée indisponible en nommant la condition manquante » : its
    # link and its invitation lack ``is_active_account``, after the attribution of its roles.
    assert commands(api, headers, table["Moreau Alix"])[-2:] == list(DEACTIVATED_LINK)


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_account_of_the_directory_or_of_a_provider_lists_neither_link_nor_invitation(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # « Un compte importé n'a pas d'écran de mot de passe » : it authenticates with its directory.
    for name in ("Bernard Dominique", "de Vries Anna", "Lefèvre Sacha"):
        assert link_commands(commands(api, headers, table[name])) == []


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
@pytest.mark.requirement("WF-ADM-0060-A")
def test_an_anonymized_local_account_lists_neither_link_nor_invitation(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # « sa réactivation est refusée » : the anonymisation is irreversible, so the account lists
    # no command that would give it a password again, while it lists the reactivation unavailable.
    gone = anonymized_account(database)
    listed = commands(api, headers, gone)
    assert link_commands(listed) == []
    assert [each["command"] for each in listed][:2] == ["reactivate", "anonymize"]


@pytest.mark.parametrize("caller_permissions", [(CONSULT,)])
@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_reader_without_users_write_lists_neither_link_nor_invitation(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # « Un utilisateur sans la permission [...] ne voit pas cette commande » : the table and
    # the account list none of them.
    assert commands(api, headers, table["Roux Inès"]) == []
    assert all(each["available_commands"] == [] for each in read(api, headers)["items"])


@pytest.mark.parametrize("caller_permissions", [(CONSULT, "users.write")])
@pytest.mark.requirement("WF-IHM-0090-A")
def test_the_table_and_the_caller_list_the_link_and_the_invitation_of_a_local_account(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # The table (listUsers) says what the account (getUser) does.
    items = {each["user_id"]: each for each in read(api, headers)["items"]}
    assert link_commands(items[str(table["Roux Inès"])]["available_commands"]) == list(
        LINK_COMMANDS
    )
    assert link_commands(items[str(table["Bernard Dominique"])]["available_commands"]) == []


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
def test_an_account_carries_the_commands_its_reader_may_exercise(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # WF-IHM-0090: the one that changes the state, the anonymisation of a deactivated account,
    # the attribution of the roles, then, for a local account, its link and its invitation.
    assert commands(api, headers, table["Roux Inès"]) == [
        available("deactivate"),
        available("set_access_roles"),
        *LINK,
    ]
    assert commands(api, headers, table["Moreau Alix"]) == [
        available("reactivate"),
        available("anonymize"),
        available("set_access_roles"),
        *DEACTIVATED_LINK,
    ]
    # The caller is the only active account that holds the administration: its deactivation is
    # unavailable, the attribution of its roles is not (WF-ADM-0120).
    alone = [
        available("deactivate", "last_administrator"),
        available("set_access_roles"),
        *LINK,
    ]
    assert commands(api, headers, CALLER) == alone
    listed = read(api, headers, "?search=camille")["items"]
    assert [each["available_commands"] for each in listed] == [alone]


@pytest.mark.parametrize("caller_permissions", [(CONSULT, "users.write")])
def test_the_attribution_of_the_roles_is_offered_only_to_who_may_change_the_roles(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    # Giving a role is managing the roles (FBS-1.2, WF-ADM-0090, #834): who changes the accounts
    # alone is offered the change of their state, not the attribution of their roles.
    assert commands(api, headers, table["Roux Inès"]) == [available("deactivate"), *LINK]
    assert commands(api, headers, table["Moreau Alix"]) == [
        available("reactivate"),
        available("anonymize"),
        *DEACTIVATED_LINK,
    ]


@pytest.mark.parametrize("caller_permissions", [(CONSULT, *ADMINISTRATION)])
def test_the_deactivation_of_an_administrator_is_available_once_another_holds_the_administration(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    second = role(database, "Administration", permissions=ADMINISTRATION)
    account(database, "Noir", "Jade", roles=(second,))
    # A deactivated holder does not count: the administration is held by an active account.
    account(database, "Gris", "Tom", state="deactivated", roles=(second,))
    assert commands(api, headers, CALLER)[0] == available("deactivate")


@pytest.mark.requirement("WF-EXP-0020-A")
def test_the_administrator_of_the_installation_is_the_account_of_its_instant(
    database: Database,
) -> None:
    # The witness creates local accounts for the platform at the instants of its chronology, before
    # the installation: the administrator is read at the instant of the installation (#2298).
    installed_at = utc_now()
    with logging_context(correlation_id="installation"), database.transaction() as session:
        create_local_account(
            session,
            Identity("Témoin", "Ancien", "temoin@example.org"),
            "kc-witness",
            Act(None, installed_at - timedelta(days=365)),
        )
        assert read_installation_administrator(session, installed_at) is None
        created = create_local_account(
            session,
            Identity("Administrateur", "Premier", "admin@example.org"),
            "kc-admin",
            Act(None, installed_at),
        )
        found = read_installation_administrator(session, installed_at)
    assert found is not None
    assert found.user_id == created.user_id
