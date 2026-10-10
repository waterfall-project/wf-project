# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The catalogue of permissions and the table of the roles, as the API gives them.

The roles are written around the service, as the lot that writes them will: these tests read.
Every answer is checked against the contract (``ContractClient``).
"""

import inspect
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import insert, select, text
from sqlalchemy.exc import ProgrammingError
from support import CONTRACT, ContractClient, bearer, operations, raw_account

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles import interface, roles
from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database

PERMISSIONS = "/api/v1/permissions"
ROLES = "/api/v1/access-roles"
SUBJECT = "7d3e2b10-5c4a-4e8f-9b21-6a0f3c8d1e42"
DAY = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
# The example of the contract that gives the catalogue as it is delivered.
WITNESS = CONTRACT.parents[2] / "fixtures" / "api" / "permissions.json"


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and give the header of its token."""
    with database.transaction() as session:
        session.execute(
            insert(UserAccount).values(
                **raw_account(
                    idp_subject=SUBJECT, first_name="Camille", email="camille@example.org"
                )
            )
        )
    return bearer(realm.token(SUBJECT, KEY))


def holder(database: Database, *, active: bool = True) -> UUID:
    """Write an account that holds no role yet, and give its identifier."""
    state = "active" if active else "deactivated"
    row = raw_account(email=f"{uuid4().hex}@example.org", state=state)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


@dataclass(frozen=True, slots=True)
class Row:
    """A role as a test writes it: its label, permissions, nature, holders, deletion and author."""

    label: str
    permissions: tuple[str, ...] = ()
    is_predefined: bool = False
    holders: tuple[UUID, ...] = ()
    deleted: bool = False
    author: UUID | None = None


def role(database: Database, label: str, **columns: Any) -> UUID:
    """Write a role around the service, as ``Row`` describes it; give its identifier."""
    row = Row(label, **columns)
    identifier = uuid4()
    with database.transaction() as session:
        session.execute(
            insert(AccessRole).values(
                id=identifier,
                label=row.label,
                is_predefined=row.is_predefined,
                deleted_at=DAY + timedelta(days=1) if row.deleted else None,
                created_at=DAY,
                created_by=row.author,
                updated_at=DAY,
                updated_by=row.author,
            )
        )
        granted = session.scalars(
            select(Permission.id).where(Permission.code.in_(row.permissions))
        ).all()
        for permission_id in granted:
            session.execute(
                insert(AccessRolePermission).values(
                    access_role_id=identifier, permission_id=permission_id
                )
            )
        for user_id in row.holders:
            session.execute(
                insert(UserAccessRole).values(user_account_id=user_id, access_role_id=identifier)
            )
    return identifier


def labels(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the labels of the table of the roles, in its order, for a query of filters and sort."""
    response = api.get(f"{ROLES}{query}", headers=headers)
    assert response.status_code == 200
    return [entry["label"] for entry in response.json()]


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


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_module_of_the_roles_has_no_command_that_deletes_one() -> None:
    names = [
        name
        for module in (roles, interface)
        for name, _ in inspect.getmembers(module, inspect.isfunction)
    ]
    assert names
    assert not [name for name in names if name.startswith(("delete", "remove", "purge", "drop"))]
    module = Path(roles.__file__).parent
    sources = "\n".join(path.read_text(encoding="utf-8") for path in module.glob("*.py"))
    assert not re.search(r"delete\(\s*AccessRole\b", sources)
    assert not re.search(r"DELETE\s+FROM\s+access_role\b", sources, re.IGNORECASE)


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
