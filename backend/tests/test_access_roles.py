# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The catalogue of permissions and the table of the roles, as the API gives them.

The roles are read as they are written around the service (``access_rows``), and written through
the API, which inscribes each write in the journal of audit. Every answer is checked against the
contract (``ContractClient``). The caller holds a role of its own, which gives it the permissions
the operations ask for (``caller_permissions``) and which the table of the roles read here leaves
out (``labels``); a test that needs its caller to hold other ones says which.
"""

import ast
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from access_rows import ADMINISTRATION, holder, role
from openapi_core import OpenAPI
from openapi_core.templating.responses.exceptions import ResponseNotFound
from realm import KEY, TestRealm
from sqlalchemy import insert, select, text
from sqlalchemy.exc import ProgrammingError
from support import CONTRACT, ContractClient, bearer, operations, raw_account

import waterfall
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles import roles
from waterfall.core.access_roles.predefined import ADMINISTRATOR
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import Database

PERMISSIONS = "/api/v1/permissions"
ROLES = "/api/v1/access-roles"
SUBJECT = "7d3e2b10-5c4a-4e8f-9b21-6a0f3c8d1e42"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
# The role of the caller, and the permissions it gives unless a test says otherwise.
CALLER_ROLE = "Habilitations de l'appelant"
CONSULT_AND_CHANGE = ("access_roles.read", "access_roles.write")
# The example of the contract that gives the catalogue as it is delivered.
WITNESS = CONTRACT.parents[2] / "fixtures" / "api" / "permissions.json"


@pytest.fixture
def caller_permissions() -> tuple[str, ...]:
    """Give the permissions the role of the caller grants: to consult and change the roles."""
    return CONSULT_AND_CHANGE


@pytest.fixture
def headers(
    database: Database, realm: TestRealm, caller_permissions: tuple[str, ...]
) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and its role; give its token's header."""
    with database.transaction() as session:
        session.execute(
            insert(UserAccount).values(
                **raw_account(
                    id=CALLER,
                    idp_subject=SUBJECT,
                    first_name="Camille",
                    email="camille@example.org",
                )
            )
        )
    role(database, CALLER_ROLE, permissions=caller_permissions, holders=(CALLER,))
    return bearer(realm.token(SUBJECT, KEY))


def labels(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the labels of the table of the roles, in its order, for a query of filters and sort.

    The role of the caller is left out, wherever the filters and the sort place it.
    """
    response = api.get(f"{ROLES}{query}", headers=headers)
    assert response.status_code == 200
    return [entry["label"] for entry in response.json() if entry["label"] != CALLER_ROLE]


def test_the_catalogue_is_the_enumeration_of_the_contract_in_its_order(
    api: ContractClient, headers: dict[str, str]
) -> None:
    response = api.get(PERMISSIONS, headers=headers)
    assert response.status_code == 200
    # Every entry, its kind and its function included, as the example of the contract gives it.
    assert response.json() == json.loads(WITNESS.read_text(encoding="utf-8"))["value"]


def test_the_journal_of_audit_has_the_permission_to_read_alone(
    api: ContractClient, headers: dict[str, str]
) -> None:
    catalogue = api.get(PERMISSIONS, headers=headers).json()
    assert [entry["code"] for entry in catalogue if entry["fbs_code"] == "FBS-1.5"] == [
        "audit_log.read"
    ]


@pytest.mark.requirement("WF-ADM-0100-A")
def test_no_operation_creates_or_changes_a_permission(
    contract: OpenAPI, services: Services
) -> None:
    # « Aucun écran ne permet de créer une permission. » : no operation of the contract writes
    # one, and the service serves none.
    declared = operations(contract)
    catalogue = {method for method, path in declared.values() if path.endswith("/permissions")}
    assert catalogue == {"GET"}
    served = create_app(services).openapi()["paths"]
    assert set(served[PERMISSIONS]) == {"get"}


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.parametrize(
    "statement",
    [
        (
            "INSERT INTO permission (id, code, kind, fbs_code, position) "
            "VALUES (gen_random_uuid(), 'reports.read', 'function_read', 'FBS-5.1', 99)"
        ),
        "UPDATE permission SET code = 'users.list' WHERE code = 'users.read'",
        "DELETE FROM permission WHERE code = 'users.read'",
    ],
)
def test_the_service_may_not_write_the_catalogue(database: Database, statement: str) -> None:
    with pytest.raises(ProgrammingError) as raised, database.engine.begin() as connection:
        connection.execute(text(statement))
    assert isinstance(raised.value.orig, psycopg.errors.InsufficientPrivilege)


def test_a_role_is_given_with_its_permissions_in_the_order_of_the_catalogue(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    author = holder(database)
    held = role(
        database,
        "Chiffreur",
        permissions=("estimate.write", "cost_settings.read", "estimate.read"),
        holders=(holder(database), holder(database, active=False)),
        author=author,
    )
    response = api.get(f"{ROLES}/{held}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["permissions"] == ["cost_settings.read", "estimate.read", "estimate.write"]
    # The holders count every account that holds the role, the deactivated ones too.
    assert (body["label"], body["is_predefined"], body["holder_count"]) == ("Chiffreur", False, 2)
    assert body["audit"]["created_by"] == {
        "kind": "user",
        "user_id": str(author),
        "display_name": "Claire Martin",
    }
    assert body["lock_version"] == 0


def test_a_predefined_role_written_by_the_platform_says_so(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    written = role(database, "Manager", is_predefined=True, permissions=("planning.read",))
    body = api.get(f"{ROLES}/{written}", headers=headers).json()
    assert (body["is_predefined"], body["holder_count"]) == (True, 0)
    assert body["audit"]["updated_by"] == {"kind": "platform"}


@pytest.mark.parametrize("path", [f"{ROLES}/{uuid4()}", f"{ROLES}/not-a-role"])
def test_an_unknown_role_is_not_found(
    api: ContractClient, headers: dict[str, str], path: str
) -> None:
    response = api.get(path, headers=headers)
    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


def test_a_deleted_role_is_no_longer_read_and_its_row_is_kept(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    deleted = role(database, "Auditeur", permissions=("audit_log.read",), deleted=True)
    role(database, "Chiffreur")
    response = api.get(f"{ROLES}/{deleted}", headers=headers)
    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
    assert labels(api, headers) == ["Chiffreur"]
    with database.transaction() as session:
        kept = session.execute(select(AccessRole.label).where(AccessRole.id == deleted)).one()
    assert tuple(kept) == ("Auditeur",)


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_service_may_not_remove_a_role_from_the_database(database: Database) -> None:
    role(database, "Chiffreur")
    with pytest.raises(ProgrammingError) as raised, database.engine.begin() as connection:
        connection.execute(text("DELETE FROM access_role"))
    assert isinstance(raised.value.orig, psycopg.errors.InsufficientPrivilege)


# What names a role in a deletion: its table, its class, or a variable that holds one. The rows of
# ``access_role_permission`` may go, and ``role_id`` is an identifier, not a role.
ROLE_NAMES = {"AccessRole", "access_role", "role", "roles"}
# A SQL text that removes rows of the table of the roles, its name quoted or qualified or not.
REMOVAL = re.compile(
    r"\b(?:DELETE\s+FROM|TRUNCATE(?:\s+TABLE)?)\s+(?:ONLY\s+)?"
    r"(?:\"?public\"?\.)?\"?access_role\"?(?!\w)",
    re.IGNORECASE,
)


def _docstrings(tree: ast.Module) -> set[int]:
    """Give the identities of the docstrings of a module, its classes and its functions."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def _names_a_role(node: ast.AST) -> bool:
    return any(
        (isinstance(part, ast.Name) and part.id in ROLE_NAMES)
        or (isinstance(part, ast.Attribute) and part.attr in ROLE_NAMES)
        for part in ast.walk(node)
    )


def role_removals(source: str) -> list[int]:
    """Give the lines of a source that remove a role: a deletion of the ORM, or a SQL text.

    A call ``delete(...)`` or ``.delete(...)`` removes a role when what it is called on or with
    names one; a text, a docstring apart, when it is SQL that deletes from or truncates the table.
    """
    tree = ast.parse(source)
    docstrings = _docstrings(tree)
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            name = function.id if isinstance(function, ast.Name) else None
            if isinstance(function, ast.Attribute):
                name = function.attr
            if name == "delete" and _names_a_role(node):
                lines.append(node.lineno)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and REMOVAL.search(node.value)
        ):
            lines.append(node.lineno)
    return lines


@pytest.mark.parametrize(
    "source",
    [
        "session.delete(role)",
        "session.execute(delete(tables.AccessRole))",
        "session.execute(sqlalchemy.delete(AccessRole).where(AccessRole.id == role_id))",
        "session.execute(AccessRole.__table__.delete())",
        "text('DELETE FROM \"access_role\" WHERE id = :id')",
        "text('delete from public.access_role')",
        "text(f'TRUNCATE access_role CASCADE')",
        "text('truncate table only access_role')",
    ],
)
def test_a_removal_of_a_role_is_found_in_a_source(source: str) -> None:
    assert role_removals(source) == [1]


@pytest.mark.parametrize(
    "source",
    [
        "session.execute(update(AccessRole).values(deleted_at=at))",
        "delete(AccessRolePermission).where(AccessRolePermission.access_role_id == role_id)",
        "session.delete(upload)",
        "text('DELETE FROM access_role_permission WHERE access_role_id = :id')",
        (
            'def mark(role):\n    """Never delete from access_role: mark the role."""\n'
            "    # delete from access_role\n"
        ),
    ],
)
def test_what_does_not_remove_a_role_is_not_found(source: str) -> None:
    assert role_removals(source) == []


@pytest.mark.requirement("WF-DAT-0080-A")
def test_no_query_of_the_service_deletes_a_role_physically() -> None:
    # The sources of the whole service, so that a query written outside the module is seen too.
    paths = sorted(Path(waterfall.__file__).parent.rglob("*.py"))
    assert Path(roles.__file__) in paths
    found = {
        str(path): lines
        for path in paths
        if (lines := role_removals(path.read_text(encoding="utf-8")))
    }
    assert found == {}


@pytest.fixture
def table(database: Database) -> dict[str, UUID]:
    """Write a table of roles whose orders differ on each column; give their identifiers."""
    one, two = holder(database), holder(database)
    return {
        "Zeta": role(database, "Zeta", is_predefined=True, holders=(one, two)),
        "alpha": role(database, "alpha"),
        "Émile": role(database, "Émile", holders=(one,)),
        "Beta": role(database, "Beta", is_predefined=True, holders=(two,)),
        "Alpha": role(database, "Alpha", holders=(one,)),
        # The search lowers every letter, not only the ASCII ones, and folds the ligatures.
        "БЮРО": role(database, "БЮРО"),
        "Straße": role(database, "Straße"),
        "Main-d'œuvre": role(database, "Main-d'œuvre"),
    }


# The table in the order of the code points, case and accents included.
IN_CODE_POINT_ORDER = ["Alpha", "Beta", "Main-d'œuvre", "Straße", "Zeta", "alpha", "Émile", "БЮРО"]


@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_roles_are_sorted_by_label_in_the_order_of_the_code_points_by_default(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    assert set(table) == set(labels(api, headers))
    assert labels(api, headers) == IN_CODE_POINT_ORDER
    assert labels(api, headers, "?sort_order=desc") == IN_CODE_POINT_ORDER[::-1]


def by_identifier(
    table: dict[str, UUID], names: list[str], *, descending: bool = False
) -> list[str]:
    """Order roles that are equal on the column of the sort by their identifier."""
    return sorted(names, key=lambda name: table[name], reverse=descending)


@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_roles_are_sorted_by_nature_the_predefined_first_equals_by_identifier(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    predefined = ["Zeta", "Beta"]
    composed = ["alpha", "Émile", "Alpha", "БЮРО", "Straße", "Main-d'œuvre"]
    assert labels(api, headers, "?sort_by=is_predefined") == (
        by_identifier(table, predefined) + by_identifier(table, composed)
    )
    assert labels(api, headers, "?sort_by=is_predefined&sort_order=desc") == (
        by_identifier(table, composed, descending=True)
        + by_identifier(table, predefined, descending=True)
    )


@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_roles_are_sorted_by_their_number_of_holders_equals_by_identifier(
    api: ContractClient, headers: dict[str, str], table: dict[str, UUID]
) -> None:
    never = by_identifier(table, ["alpha", "БЮРО", "Straße", "Main-d'œuvre"])
    once = by_identifier(table, ["Émile", "Beta", "Alpha"])
    assert labels(api, headers, "?sort_by=holder_count") == [*never, *once, "Zeta"]
    assert labels(api, headers, "?sort_by=holder_count&sort_order=desc") == [
        "Zeta",
        *reversed(once),
        *reversed(never),
    ]


@pytest.mark.parametrize(
    ("query", "kept"),
    [
        # The search ignores case and accents, and a sign of a pattern is a letter like another.
        ("?search=EMILE", ["Émile"]),
        ("?search=alph", ["Alpha", "alpha"]),
        ("?search=%25", []),
        ("?search=бюро", ["БЮРО"]),
        ("?search=strasse", ["Straße"]),
        ("?search=main-d'oeuvre", ["Main-d'œuvre"]),
        ("?is_predefined=true", ["Beta", "Zeta"]),
        ("?is_predefined=false", ["Alpha", "Main-d'œuvre", "Straße", "alpha", "Émile", "БЮРО"]),
        ("?holder_count_min=1&holder_count_max=1", ["Alpha", "Beta", "Émile"]),
        ("?holder_count_max=0", ["Main-d'œuvre", "Straße", "alpha", "БЮРО"]),
        ("?holder_count_min=2", ["Zeta"]),
        # A bound beyond the integers of the database is well formed, and kept as it is said.
        (f"?holder_count_min={10**30}", []),
        (f"?holder_count_max={10**30}", IN_CODE_POINT_ORDER),
        # The filters combine, and combine with the sort.
        ("?is_predefined=false&holder_count_min=1&sort_order=desc", ["Émile", "Alpha"]),
    ],
)
def test_the_table_of_the_roles_is_filtered_on_each_of_its_columns(
    api: ContractClient,
    headers: dict[str, str],
    table: dict[str, UUID],
    query: str,
    kept: list[str],
) -> None:
    assert set(table) >= set(kept)
    assert labels(api, headers, query) == kept


def test_the_table_of_the_roles_is_not_paginated_and_gives_every_role_kept(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    for index in range(60):
        role(database, f"Rôle {index:02}")
    assert len(labels(api, headers)) == 60


def problem(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "?holder_count_min=2&holder_count_max=1",
            [
                {
                    "pointer": "/query/holder_count_max",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": 2},
                }
            ],
        ),
        (
            "?holder_count_min=-1",
            [{"pointer": "/query/holder_count_min", "code": "NUMBER_INVALID"}],
        ),
        (
            "?holder_count_max=many",
            [{"pointer": "/query/holder_count_max", "code": "NUMBER_INVALID"}],
        ),
        # Beyond the digits Python reads in an integer, still a malformed number (#743).
        (
            f"?holder_count_min={'9' * 5000}",
            [{"pointer": "/query/holder_count_min", "code": "NUMBER_INVALID"}],
        ),
        # The database refuses a text that holds a NUL: the field refuses it first.
        ("?search=%00", [{"pointer": "/query/search", "code": "VALIDATION_FAILED"}]),
    ],
)
def test_a_filter_that_is_malformed_or_inverted_is_refused(
    api: ContractClient, headers: dict[str, str], query: str, fields: list[dict[str, Any]]
) -> None:
    assert problem(api.get(f"{ROLES}{query}", headers=headers)) == (
        422,
        "VALIDATION_FAILED",
        fields,
    )


@pytest.mark.parametrize("path", [PERMISSIONS, ROLES, f"{ROLES}/{uuid4()}"])
def test_the_roles_and_the_catalogue_are_read_by_a_known_caller_only(
    api: ContractClient, path: str
) -> None:
    assert problem(api.get(path))[:2] == (401, "SESSION_REQUIRED")


# The caller as the rows and the journal name it.
CAMILLE = {"kind": "user", "user_id": str(CALLER), "display_name": "Camille Martin"}


def journal(database: Database) -> list[AuditEntry]:
    """Read the inscriptions of the journal of audit, in their order."""
    with database.transaction() as session:
        entries = session.scalars(select(AuditEntry).order_by(AuditEntry.id)).all()
        session.expunge_all()
    return list(entries)


def kept(database: Database, role_id: UUID) -> AccessRole:
    """Read the row of a role as the table keeps it, deleted or not."""
    with database.transaction() as session:
        row = session.get_one(AccessRole, role_id)
        session.expunge(row)
    return row


@pytest.mark.requirement("WF-SEC-0030-A")
def test_a_role_is_composed_of_any_permissions_and_its_creation_inscribed(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    sent: dict[str, object] = {
        "label": "Chiffreur",
        "permissions": ["estimate.write", "audit_log.read", "users.read"],
    }
    response = api.post(ROLES, headers=headers, json=sent)
    assert response.status_code == 201
    body = response.json()
    assert body["permissions"] == ["users.read", "audit_log.read", "estimate.write"]
    assert (body["label"], body["is_predefined"], body["holder_count"]) == ("Chiffreur", False, 0)
    assert (body["audit"]["created_by"], body["lock_version"]) == (CAMILLE, 0)
    assert api.get(f"{ROLES}/{body['access_role_id']}", headers=headers).json() == body
    [entry] = journal(database)
    assert (entry.action, entry.object_kind, str(entry.object_id), entry.object_label) == (
        "access_role_create",
        "access_role",
        body["access_role_id"],
        "Chiffreur",
    )
    assert (entry.actor_user_id, entry.actor_display_name) == (CALLER, "Camille Martin")
    assert entry.params == {"permissions": body["permissions"]}
    assert entry.occurred_at == datetime.fromisoformat(body["audit"]["created_at"])
    assert entry.correlation_id == response.headers[HEADER]


def test_a_permission_outside_the_catalogue_is_refused(
    api: ContractClient, headers: dict[str, str]
) -> None:
    sent: dict[str, object] = {
        "label": "Rapports",
        "permissions": ["planning.read", "reports.read"],
    }
    assert problem(api.post(ROLES, headers=headers, json=sent)) == (
        422,
        "VALIDATION_FAILED",
        [{"pointer": "/permissions/1", "code": "VALIDATION_FAILED"}],
    )
    assert labels(api, headers) == []


@pytest.mark.parametrize(
    "operation",
    [
        "createAccessRole",
        # The contract declares no 422 for the change of a role: the answer, the one every refused
        # value gets, is not the contract's until it does (#748).
        pytest.param(
            "updateAccessRole",
            marks=pytest.mark.xfail(raises=ResponseNotFound, strict=True, reason="#748"),
        ),
    ],
)
def test_a_label_that_holds_a_nul_is_refused_at_its_field(
    api: ContractClient, database: Database, headers: dict[str, str], operation: str
) -> None:
    # PostgreSQL refuses a text that holds a NUL: the field refuses it first, not the database.
    written = role(database, "Chiffreur")
    sent: dict[str, object] = {"label": "Chif\x00freur", "permissions": [], "lock_version": 0}
    if operation == "createAccessRole":
        response = api.post(ROLES, headers=headers, json=sent)
    else:
        response = api.patch(f"{ROLES}/{written}", headers=headers, json=sent)
    assert problem(response) == (
        422,
        "VALIDATION_FAILED",
        [{"pointer": "/label", "code": "VALIDATION_FAILED"}],
    )
    assert (labels(api, headers), journal(database)) == (["Chiffreur"], [])


# The predefined « Administrateur » alone gives the caller what it does here.
@pytest.mark.requirement("WF-ADM-0010-A")
@pytest.mark.parametrize("caller_permissions", [()])
def test_a_predefined_role_is_renamed_changed_and_deleted_when_no_account_holds_it(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # « Un administrateur renomme un rôle prédéfini et en modifie les permissions, et il supprime
    # sans erreur un rôle prédéfini qu'aucun compte ne porte. »
    role(
        database, "Administrateur", permissions=ADMINISTRATOR, is_predefined=True, holders=(CALLER,)
    )
    pilot = role(
        database,
        "Chef de projet",
        permissions=("planning.read", "planning.write"),
        is_predefined=True,
        holders=(holder(database),),
    )
    unheld = role(database, "Manager", permissions=("planning.read",), is_predefined=True)
    change = {"label": "Pilote", "permissions": ["risks.read", "planning.read"], "lock_version": 0}
    response = api.patch(f"{ROLES}/{pilot}", headers=headers, json=change)
    assert response.status_code == 200
    body = response.json()
    assert (body["label"], body["permissions"], body["is_predefined"]) == (
        "Pilote",
        ["planning.read", "risks.read"],
        True,
    )
    assert (body["holder_count"], body["lock_version"], body["audit"]["updated_by"]) == (
        1,
        1,
        CAMILLE,
    )
    assert api.delete(f"{ROLES}/{unheld}", headers=headers).status_code == 204
    assert labels(api, headers) == ["Administrateur", "Pilote"]


@pytest.mark.requirement("WF-SEC-0030-A")
def test_a_change_is_inscribed_with_what_it_grants_withdraws_and_renames(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    changed = role(database, "Chef de projet", permissions=("planning.read", "planning.write"))
    written: list[datetime] = []
    for label, permissions, version in [
        ("Pilote", ["planning.read", "risks.read"], 0),
        ("Pilote", ["planning.read"], 1),
    ]:
        sent: dict[str, object] = {
            "label": label,
            "permissions": permissions,
            "lock_version": version,
        }
        response = api.patch(f"{ROLES}/{changed}", headers=headers, json=sent)
        assert response.status_code == 200
        written.append(datetime.fromisoformat(response.json()["audit"]["updated_at"]))
    renamed, withdrawn = journal(database)
    assert [renamed.occurred_at, withdrawn.occurred_at] == written
    assert {entry.action for entry in (renamed, withdrawn)} == {"access_role_update"}
    assert (renamed.object_id, renamed.object_label, renamed.actor_user_id) == (
        changed,
        "Pilote",
        CALLER,
    )
    assert renamed.params == {
        "permissions_granted": ["risks.read"],
        "permissions_withdrawn": ["planning.write"],
        "previous_label": "Chef de projet",
    }
    # The label unchanged, the inscription does not say a previous one.
    assert withdrawn.params == {"permissions_granted": [], "permissions_withdrawn": ["risks.read"]}


def test_a_change_on_a_version_no_longer_current_is_refused_and_writes_nothing(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    changed = role(database, "Chiffreur", permissions=("estimate.read",))
    first = {"label": "Chiffrage", "permissions": ["estimate.read"], "lock_version": 0}
    assert api.patch(f"{ROLES}/{changed}", headers=headers, json=first).status_code == 200
    stale: dict[str, object] = {"label": "Devis", "permissions": [], "lock_version": 0}
    response = api.patch(f"{ROLES}/{changed}", headers=headers, json=stale)
    assert response.status_code == 412
    assert response.json()["code"] == "STALE_LOCK_VERSION"
    assert response.json()["params"] == {"expected_lock_version": 1}
    body = api.get(f"{ROLES}/{changed}", headers=headers).json()
    assert (body["label"], body["permissions"], body["lock_version"]) == (
        "Chiffrage",
        ["estimate.read"],
        1,
    )
    assert len(journal(database)) == 1


@pytest.mark.requirement("WF-DAT-0080-A")
@pytest.mark.requirement("WF-SEC-0030-A")
def test_a_deleted_role_is_no_longer_read_its_row_kept_and_its_deletion_inscribed(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # « un rôle supprimé n'est plus lu ni attribuable, et sa ligne est conservée, ce que le
    # journal d'audit et les attributions passées citent » — the side of the writes.
    deleted = role(database, "Auditeur", permissions=("audit_log.read",))
    role(database, "Chiffreur")
    response = api.delete(f"{ROLES}/{deleted}", headers=headers)
    assert (response.status_code, response.content) == (204, b"")
    assert api.get(f"{ROLES}/{deleted}", headers=headers).status_code == 404
    assert labels(api, headers) == ["Chiffreur"]
    row = kept(database, deleted)
    assert (row.label, row.deleted_at is not None, row.lock_version, row.updated_by) == (
        "Auditeur",
        True,
        1,
        CALLER,
    )
    [entry] = journal(database)
    assert (entry.action, entry.object_id, entry.object_label, entry.actor_user_id) == (
        "access_role_delete",
        deleted,
        "Auditeur",
        CALLER,
    )
    assert entry.occurred_at == row.deleted_at
    assert entry.correlation_id == response.headers[HEADER]


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_a_deleted_role_is_neither_changed_nor_deleted_again(
    api: ContractClient, database: Database, headers: dict[str, str], method: str
) -> None:
    deleted = role(database, "Auditeur", deleted=True)
    for path in (f"{ROLES}/{deleted}", f"{ROLES}/{uuid4()}"):
        sent: dict[str, object] = {"label": "Auditrice", "permissions": [], "lock_version": 0}
        response = api.request(method, path, headers=headers, json=sent)
        assert problem(response)[:2] == (404, "NOT_FOUND")
    row = kept(database, deleted)
    assert (row.label, row.lock_version, journal(database)) == ("Auditeur", 0, [])


@pytest.mark.requirement("WF-ADM-0090-A")
@pytest.mark.parametrize("active", [True, False])
def test_a_role_an_account_holds_is_not_deleted(
    api: ContractClient, database: Database, headers: dict[str, str], *, active: bool
) -> None:
    # « La suppression d'un rôle est refusée tant qu'un compte le porte. » — a deactivated
    # account holds it too.
    held = role(database, "Chiffreur", holders=(holder(database, active=active),))
    assert problem(api.delete(f"{ROLES}/{held}", headers=headers)) == (
        409,
        "ACCESS_ROLE_IN_USE",
        [],
    )
    assert (labels(api, headers), kept(database, held).deleted_at, journal(database)) == (
        ["Chiffreur"],
        None,
        [],
    )


@pytest.mark.requirement("WF-ADM-0010-A")
def test_the_administrator_role_its_holder_holds_is_not_deleted(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # « La suppression du rôle « administrateur » qu'il porte est refusée (WF-ADM-0090,
    # WF-ADM-0120). »
    held = role(
        database, "Administrateur", permissions=ADMINISTRATOR, is_predefined=True, holders=(CALLER,)
    )
    assert problem(api.delete(f"{ROLES}/{held}", headers=headers))[:2] == (
        409,
        "ACCESS_ROLE_IN_USE",
    )
    assert labels(api, headers) == ["Administrateur"]


# The caller changes the roles by ``Direction`` alone, which it may then take from itself.
@pytest.mark.parametrize("caller_permissions", [("access_roles.read",)])
@pytest.mark.parametrize("withdrawn", ADMINISTRATION)
def test_a_change_that_takes_the_administration_from_the_last_administrator_is_refused(
    api: ContractClient, database: Database, headers: dict[str, str], withdrawn: str
) -> None:
    # A deactivated account that holds the role is no administrator: Camille is the last one.
    direction = role(
        database,
        "Direction",
        permissions=(*ADMINISTRATION, "users.read"),
        holders=(CALLER, holder(database, active=False)),
    )
    kept_ones = [code for code in ("users.read", *ADMINISTRATION) if code != withdrawn]
    sent: dict[str, object] = {"label": "Direction", "permissions": kept_ones, "lock_version": 0}
    assert problem(api.patch(f"{ROLES}/{direction}", headers=headers, json=sent)) == (
        409,
        "LAST_ADMINISTRATOR",
        [],
    )
    body = api.get(f"{ROLES}/{direction}", headers=headers).json()
    assert (body["permissions"], body["lock_version"], journal(database)) == (
        ["users.read", "users.write", "access_roles.write"],
        0,
        [],
    )


# As above, ``Direction`` alone makes the caller an administrator; without a second one, the
# same change is refused.
@pytest.mark.parametrize("caller_permissions", [("access_roles.read",)])
@pytest.mark.parametrize("second", [True, False])
def test_the_administration_is_withdrawn_once_a_second_active_account_holds_it(
    api: ContractClient, database: Database, headers: dict[str, str], second: bool
) -> None:
    direction = role(database, "Direction", permissions=ADMINISTRATION, holders=(CALLER,))
    if second:
        role(database, "Administration", permissions=ADMINISTRATION, holders=(holder(database),))
    sent: dict[str, object] = {
        "label": "Direction",
        "permissions": ["users.write"],
        "lock_version": 0,
    }
    response = api.patch(f"{ROLES}/{direction}", headers=headers, json=sent)
    if second:
        assert (response.status_code, response.json()["permissions"]) == (200, ["users.write"])
    else:
        assert problem(response) == (409, "LAST_ADMINISTRATOR", [])


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", ROLES), ("PATCH", f"{ROLES}/{uuid4()}"), ("DELETE", f"{ROLES}/{uuid4()}")],
)
def test_the_roles_are_written_by_a_known_caller_only(
    api: ContractClient, method: str, path: str
) -> None:
    sent: dict[str, object] = {"label": "Chiffreur", "permissions": [], "lock_version": 0}
    assert problem(api.request(method, path, json=sent))[:2] == (401, "SESSION_REQUIRED")
