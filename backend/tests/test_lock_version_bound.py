# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The write counter bounded by the contract: beyond what the database holds, a validation refusal.

``LockVersion`` carries ``maximum: 2147483647``, the largest integer of the ``lock_version``
columns (#2232, EP-23/US-1810): a counter beyond it is refused by the model the contract generates,
or by the bound of a query parameter, before the database is asked — where PostgreSQL refused it
with an internal error. A correction of the contract and the service: no requirement is cited.
The roles stand for every write that carries a counter; ``test_contract_declarations.py`` holds
the bound of the four query parameters the service serves against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from access_rows import role
from projects_support import PROJECTS
from projects_support import scene as make_scene
from realm import KEY, TestRealm
from sqlalchemy import insert, select
from support import ContractClient, bearer, raw_account

from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from waterfall.platform.database import Database

ROLES = "/api/v1/access-roles"
# An identifier no row holds: the request is validated before any row is looked up.
UNKNOWN = UUID("5b0e7c3a-91d4-4c26-8f1a-2e6d9b4a7c15")
SUBJECT = "3a8f1c62-7d4e-4b09-a5c3-9e2f6d1b8a74"
CALLER = UUID("0192a1b2-0000-7000-8000-0000000c0b70")
# The bound of ``LockVersion``, and the first counter beyond it.
BOUND = 2147483647
BEYOND = BOUND + 1


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write the account of the caller, who may change the roles; give its token's header."""
    with database.transaction() as session:
        session.execute(
            insert(UserAccount).values(
                **raw_account(id=CALLER, idp_subject=SUBJECT, email="dominique@example.org")
            )
        )
    role(
        database,
        "Habilitations de l'appelant",
        permissions=("access_roles.read", "access_roles.write"),
        holders=(CALLER,),
    )
    return bearer(realm.token(SUBJECT, KEY))


def update(counter: int) -> dict[str, object]:
    """Give the body of a renaming of a role that carries a counter."""
    return {"label": "x", "permissions": [], "lock_version": counter}


def refusal(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


def beyond(pointer: str) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the refusal of a counter beyond the bound, at a pointer."""
    field = {"pointer": pointer, "code": "VALUE_OUT_OF_RANGE", "params": {"maximum": BOUND}}
    return 422, "VALIDATION_FAILED", [field]


def untouched(database: Database, role_id: UUID) -> tuple[str, int, bool, list[AuditEntry]]:
    """Read the label, the counter and the deletion of a role, and the journal of audit."""
    with database.transaction() as session:
        row = session.get_one(AccessRole, role_id)
        entries = list(session.scalars(select(AuditEntry)).all())
        return row.label, row.lock_version, row.deleted_at is not None, entries


def test_a_counter_beyond_the_bound_in_a_body_is_refused_by_the_validation(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    written = role(database, "Chiffreur")
    response = api.patch(f"{ROLES}/{written}", headers=headers, json=update(BEYOND))
    assert refusal(response) == beyond("/lock_version")
    assert untouched(database, written) == ("Chiffreur", 0, False, [])


def test_a_counter_beyond_the_bound_is_refused_before_the_object_is_looked_up(
    api: ContractClient, headers: dict[str, str]
) -> None:
    # Refused by the model of the contract, not by the database: an object no row holds is
    # refused on the counter as one that exists, 422 and not 404.
    response = api.patch(f"{ROLES}/{UNKNOWN}", headers=headers, json=update(BEYOND))
    assert refusal(response) == beyond("/lock_version")


def test_a_counter_beyond_the_bound_in_a_query_is_refused_by_the_validation(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    written = role(database, "Chiffreur")
    response = api.delete(f"{ROLES}/{written}", headers=headers, params={"lock_version": BEYOND})
    assert refusal(response) == beyond("/query/lock_version")
    assert untouched(database, written) == ("Chiffreur", 0, False, [])
    unknown = api.delete(f"{ROLES}/{UNKNOWN}", headers=headers, params={"lock_version": BEYOND})
    assert refusal(unknown) == beyond("/query/lock_version")


@pytest.mark.parametrize(
    "tail",
    [
        "subprojects/{unknown}",
        "revisions/{unknown}",
        "revisions/{unknown}/structures/{unknown}/nodes/{unknown}",
    ],
    ids=["deleteSubproject", "abandonRevision", "deleteNode"],
)
def test_a_counter_beyond_the_bound_in_a_query_is_refused_on_the_other_deletions(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, tail: str
) -> None:
    # The project exists, as the permission is read first; the object under it need not.
    stage = make_scene(api, owner, database, realm)
    path = f"{PROJECTS}/{stage.project['project_id']}/{tail.format(unknown=UNKNOWN)}"
    response = api.delete(path, headers=stage.manager.headers, params={"lock_version": BEYOND})
    assert refusal(response) == beyond("/query/lock_version")


@pytest.mark.parametrize("write", ["patch", "delete"])
def test_a_counter_at_the_bound_reaches_the_database_and_is_stale(
    api: ContractClient, database: Database, headers: dict[str, str], write: str
) -> None:
    # The bound itself is a counter the columns hold: compared in SQL, it is stale, 412, and
    # PostgreSQL raises nothing.
    written = role(database, "Chiffreur")
    if write == "patch":
        response = api.patch(f"{ROLES}/{written}", headers=headers, json=update(BOUND))
    else:
        response = api.delete(f"{ROLES}/{written}", headers=headers, params={"lock_version": BOUND})
    assert response.status_code == 412
    assert response.json()["code"] == "STALE_LOCK_VERSION"
    assert untouched(database, written) == ("Chiffreur", 0, False, [])
