# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evaluation of an action: the effective permissions of the caller, and the refusals.

Each person is an account written around the service, with the roles a test gives it
(``access_rows``), and calls the API with a token of the realm of test. Every answer is checked
against the contract (``ContractClient``).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from access_rows import ADMINISTRATION, role
from fastapi.routing import APIRoute
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import insert, select
from support import ContractClient, bearer, operations, raw_account

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.evaluation import Requires
from waterfall.core.access_roles.interface import (
    PERMISSION_MISSING,
    Actor,
    granted_permissions,
    require,
)
from waterfall.core.access_roles.tables import AccessRole, UserAccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import Database
from waterfall.platform.errors import ForbiddenError, NotFoundError

if TYPE_CHECKING:
    from starlette.routing import BaseRoute

ME = "/api/v1/me"
ROLES = "/api/v1/access-roles"
CONSULT = "access_roles.read"
CHANGE = "access_roles.write"
# A change of a role, as the front sends it.
CHANGED: dict[str, object] = {
    "label": "Pilote",
    "permissions": ["planning.read"],
    "lock_version": 0,
}


type Person = Callable[..., dict[str, str]]


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts: each holds the roles it is given, and has its token's header."""

    def make(*roles: UUID) -> dict[str, str]:
        subject = f"subject-{uuid4()}"
        row = raw_account(idp_subject=subject, email=f"{uuid4().hex}@example.org")
        with database.transaction() as session:
            session.execute(insert(UserAccount).values(**row))
            for held in roles:
                session.execute(
                    insert(UserAccessRole).values(user_account_id=row["id"], access_role_id=held)
                )
        return bearer(realm.token(subject, KEY))

    return make


def me(api: ContractClient, headers: dict[str, str]) -> dict[str, Any]:
    """Read the account of the caller."""
    response = api.get(ME, headers=headers)
    assert response.status_code == 200
    return response.json()


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def journal(database: Database) -> list[AuditEntry]:
    """Read the inscriptions of the journal of audit."""
    with database.transaction() as session:
        return list(session.scalars(select(AuditEntry)).all())


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_caller_knows_its_effective_permissions_the_union_of_its_roles_not_deleted(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « Un utilisateur connaît la liste de ses permissions effectives » : those of its roles, each
    # once, in the order of the catalogue; a deleted role gives none, and is not named.
    estimating = role(database, "Chiffreur", permissions=("estimate.write", "estimate.read"))
    reading = role(database, "Lecteur", permissions=("estimate.read", "users.read"))
    deleted = role(database, "Auditeur", permissions=("audit_log.read",), deleted=True)
    headers = person(reading, deleted, estimating)
    account = me(api, headers)
    assert account["permissions"] == ["users.read", "estimate.read", "estimate.write"]
    assert (account["access_role_ids"], account["access_role_labels"]) == (
        [str(estimating), str(reading)],
        ["Chiffreur", "Lecteur"],
    )


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_effective_permissions_change_at_the_next_request_once_a_role_is_changed(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « … et elle change immédiatement lorsqu'un de ses rôles est modifié. » : the same token, the
    # next request, no sign-in between.
    administration = role(database, "Habilitations", permissions=(CONSULT, CHANGE))
    administrator = person(administration)
    estimating = role(database, "Chiffreur", permissions=("estimate.read",))
    headers = person(estimating)
    assert me(api, headers)["permissions"] == ["estimate.read"]
    sent: dict[str, object] = {
        "label": "Chiffrage",
        "permissions": ["estimate.read", "estimate.write"],
        "lock_version": 0,
    }
    response = api.patch(f"{ROLES}/{estimating}", headers=administrator, json=sent)
    assert response.status_code == 200
    account = me(api, headers)
    assert account["permissions"] == ["estimate.read", "estimate.write"]
    assert account["access_role_labels"] == ["Chiffrage"]


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_permission_withdrawn_from_a_role_is_no_longer_effective_at_the_next_request(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « … et elle change immédiatement lorsqu'un de ses rôles est modifié. » : a permission
    # withdrawn leaves the list at the next request — the same token, no sign-in between. The
    # refusal of the operation it opened follows: the request is evaluated against that list. A
    # second administrator keeps the change clear of the guard of the last one.
    first = person(role(database, "Administration", permissions=(CONSULT, *ADMINISTRATION)))
    held = role(database, "Habilitations", permissions=(CONSULT, *ADMINISTRATION))
    headers = person(held)
    assert me(api, headers)["permissions"] == ["users.write", CONSULT, CHANGE]
    withdrawn: dict[str, object] = {
        "label": "Habilitations",
        "permissions": [CONSULT, "users.write"],
        "lock_version": 0,
    }
    assert api.patch(f"{ROLES}/{held}", headers=first, json=withdrawn).status_code == 200
    assert me(api, headers)["permissions"] == ["users.write", CONSULT]
    response = api.patch(f"{ROLES}/{held}", headers=headers, json={**CHANGED, "lock_version": 1})
    assert refusal(response) == (403, PERMISSION_MISSING, {"missing_permission": CHANGE})


@pytest.mark.parametrize("headed", [False, True])
def test_a_body_that_cannot_be_read_is_refused_before_the_caller_is_evaluated(
    api: ContractClient, database: Database, person: Person, headed: bool
) -> None:
    # The body is read before the dependencies run: unreadable, it is refused first (400), to an
    # unknown caller as to one without the permission.
    headers = person(role(database, "Consultation des rôles", permissions=(CONSULT,)))
    sent = {"content-type": "application/json", **(headers if headed else {})}
    response = api.post(ROLES, headers=sent, content="{nope")
    assert refusal(response)[:2] == (400, "MALFORMED_REQUEST")


@pytest.mark.parametrize(
    "asked_for",
    [
        ("POST", False, {"label": "Chiffreur", "permissions": ["estimate.read"]}),
        ("PATCH", True, CHANGED),
        ("DELETE", True, None),
        # A request no screen would send is refused for the permission first, not for its body.
        ("POST", False, {"label": "", "permissions": ["reports.read"]}),
        ("PATCH", True, {"label": "Pilote"}),
    ],
)
def test_an_operation_asked_without_its_permission_is_refused_naming_it(
    api: ContractClient,
    database: Database,
    person: Person,
    asked_for: tuple[str, bool, dict[str, object] | None],
) -> None:
    # Criterion of US-0390: « une opération demandée sans sa permission est refusée par l'API,
    # quel que soit ce que le front présente, et le refus nomme la permission manquante. »
    consulting = role(database, "Consultation des rôles", permissions=(CONSULT,))
    headers = person(consulting)
    method, on_a_role, sent = asked_for
    path = f"{ROLES}/{consulting}" if on_a_role else ROLES
    response = api.request(method, path, headers=headers, json=sent)
    assert refusal(response) == (403, PERMISSION_MISSING, {"missing_permission": CHANGE})
    # Nothing is written: neither a role, nor a change, nor an inscription.
    with database.transaction() as session:
        rows = session.execute(select(AccessRole.label, AccessRole.deleted_at)).all()
    assert [tuple(row) for row in rows] == [("Consultation des rôles", None)]
    assert journal(database) == []


@pytest.mark.parametrize(
    "asked_for",
    [
        ("GET", ROLES, None),
        ("GET", f"{ROLES}/{{role}}", None),
        ("PATCH", f"{ROLES}/{{role}}", CHANGED),
        ("DELETE", f"{ROLES}/{{role}}", None),
    ],
)
@pytest.mark.parametrize("granted", [(), (CHANGE,)])
def test_the_roles_do_not_exist_for_a_caller_who_may_not_consult_them(
    api: ContractClient,
    database: Database,
    person: Person,
    asked_for: tuple[str, str, dict[str, object] | None],
    granted: tuple[str, ...],
) -> None:
    # Without the permission to consult, even with that to change: 404, never 403.
    method, path, sent = asked_for
    held = role(database, "Écriture seule", permissions=granted)
    headers = person(held)
    response = api.request(method, path.format(role=held), headers=headers, json=sent)
    assert refusal(response) == (404, "NOT_FOUND", {})
    assert journal(database) == []


@pytest.mark.requirement("WF-ADM-0110-A")
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_an_unknown_role_and_a_role_not_consultable_get_the_same_answer(
    api: ContractClient, database: Database, person: Person, method: str
) -> None:
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » : constated for a role, the object the API serves an address of today.
    consulting = role(database, "Habilitations", permissions=(CONSULT, CHANGE))
    may_consult = person(consulting)
    hidden = role(database, "Chiffreur", permissions=("estimate.read",))
    may_not = person(hidden)
    sent = CHANGED if method == "PATCH" else None
    unknown = api.request(method, f"{ROLES}/{uuid4()}", headers=may_consult, json=sent)
    not_consultable = api.request(method, f"{ROLES}/{hidden}", headers=may_not, json=sent)
    # The same status, the same type, the same body but for the correlation of each request.
    assert unknown.status_code == not_consultable.status_code == 404
    assert unknown.headers["content-type"] == not_consultable.headers["content-type"]
    bodies = [answer.json() for answer in (unknown, not_consultable)]
    assert [body.pop("correlation_id") for body in bodies] == [
        unknown.headers[HEADER],
        not_consultable.headers[HEADER],
    ]
    assert bodies[0] == bodies[1] == {"code": "NOT_FOUND", "status": 404}


def test_an_account_without_any_role_reads_its_own_account_and_the_catalogue(
    api: ContractClient, person: Person
) -> None:
    # The operations the contract refuses to no caller it knows ask for no permission.
    headers = person()
    assert me(api, headers)["permissions"] == []
    assert api.get("/api/v1/permissions", headers=headers).status_code == 200
    assert api.get(ROLES, headers=headers).status_code == 404


# The permissions each served operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "getLiveness": (),
    "getMe": (),
    "closeMySessions": (),
    "listPermissions": (),
    "listAccessRoles": (CONSULT,),
    "getAccessRole": (CONSULT,),
    "createAccessRole": (CHANGE,),
    "updateAccessRole": (CONSULT, CHANGE),
    "deleteAccessRole": (CONSULT, CHANGE),
}


def asked(route: APIRoute) -> tuple[str, ...]:
    """Give the permissions a route asks for, by its dependencies."""
    return tuple(
        permission
        for depends in route.dependencies
        if isinstance(depends.dependency, Requires)
        for permission in depends.dependency.permissions
    )


def refused_without(permission: str) -> str:
    """Give the status the evaluation refuses an actor without ``permission`` by."""
    with pytest.raises((NotFoundError, ForbiddenError)) as refused:
        require(Actor(uuid4(), ()), permission)
    return str(refused.value.status)


def test_every_served_operation_asks_for_the_permission_the_contract_refuses_it_without(
    contract: OpenAPI, services: Services
) -> None:
    # A permission to consult missing is a 404, any other a 403: the operation declares the
    # refusal it may give; one that declares neither asks for nothing.
    served: list[BaseRoute] = []
    for included in create_app(services).routes:
        router = getattr(included, "original_router", None)
        served.extend(cast("list[BaseRoute]", router.routes) if router else [included])
    routes = {
        route.operation_id: route
        for route in served
        if isinstance(route, APIRoute) and route.operation_id
    }
    assert {name: asked(route) for name, route in routes.items()} == ASKED
    declared = operations(contract)
    for name, permissions in ASKED.items():
        method, path = declared[name]
        relative = path.removeprefix((contract.spec / "servers" / 0 / "url").read_value())
        responses = set((contract.spec / "paths" / relative / method.lower() / "responses").keys())
        needed = {refused_without(code) for code in permissions}
        assert needed <= responses, name
        if not permissions:
            assert not {"403", "404"} & responses, name


def test_the_permissions_granted_by_given_roles_are_their_union_deleted_ones_apart(
    database: Database,
) -> None:
    estimating = role(database, "Chiffreur", permissions=("estimate.write", "estimate.read"))
    reading = role(database, "Lecteur", permissions=("estimate.read", "users.read"))
    deleted = role(database, "Auditeur", permissions=("audit_log.read",), deleted=True)
    role(database, "Pilote", permissions=("planning.read",))
    with database.transaction() as session:
        assert granted_permissions(session, [reading, deleted, estimating]) == (
            "users.read",
            "estimate.read",
            "estimate.write",
        )
        assert granted_permissions(session, []) == ()


def test_an_actor_passes_with_the_permission_and_is_refused_without_it() -> None:
    actor = Actor(uuid4(), ("users.read", "planning.write"))
    require(actor, "users.read")
    require(actor, "planning.write")
    with pytest.raises(NotFoundError) as hidden:
        require(actor, "planning.read")
    assert (hidden.value.code, dict(hidden.value.params)) == ("NOT_FOUND", {})
    with pytest.raises(ForbiddenError) as forbidden:
        require(actor, "users.write")
    assert (forbidden.value.code, dict(forbidden.value.params)) == (
        PERMISSION_MISSING,
        {"missing_permission": "users.write"},
    )
