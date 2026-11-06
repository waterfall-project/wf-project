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

import asked_actual_cost_mapping
import asked_calendars
import asked_cost_types
import asked_hourly_rates
import asked_org_nodes
import asked_reference
import asked_reference_settings
import asked_resource_roles
import pytest
from access_rows import ADMINISTRATION, role
from fastapi.routing import APIRoute
from realm import KEY, TestRealm
from sqlalchemy import insert, select
from starlette.requests import Request
from support import REFERENCE_PARTS, ContractClient, bearer, operations, raw_account

from waterfall.api.app import create_app
from waterfall.api.evaluation import Requires, RequiresForInactive
from waterfall.core.access_roles.interface import (
    PERMISSION_MISSING,
    Actor,
    holding,
    require,
)
from waterfall.core.access_roles.predefined import ADMINISTRATOR, PROJECT_MANAGER
from waterfall.core.access_roles.tables import AccessRole, UserAccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.correlation import HEADER
from waterfall.platform.errors import ForbiddenError, NotFoundError

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from starlette.routing import BaseRoute
    from support import ReferenceSessions

    from waterfall.api.authentication import Services
    from waterfall.platform.database import Database

ME = "/api/v1/me"
ROLES = "/api/v1/access-roles"
USERS = "/api/v1/users"
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


@pytest.mark.requirement("WF-ADM-0090-A")
def test_an_account_given_two_roles_holds_the_permissions_of_both(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « Un utilisateur portant deux rôles dispose des permissions des deux. » : given by the
    # attribution of its roles, each opens its operation at the next request of the account.
    administrator = person(
        role(database, "Comptes", permissions=("users.read", "users.write", CHANGE))
    )
    accounts = role(database, "Lecture des comptes", permissions=("users.read",))
    roles = role(database, "Lecture des rôles", permissions=(CONSULT,))
    headers = person()
    assert [api.get(path, headers=headers).status_code for path in (USERS, ROLES)] == [404, 404]
    sent = {"access_role_ids": [str(accounts), str(roles)], "lock_version": 0}
    path = f"{USERS}/{me(api, headers)['user_id']}/access-roles"
    assert api.request("PUT", path, headers=administrator, json=sent).status_code == 200
    assert me(api, headers)["permissions"] == ["users.read", CONSULT]
    assert [api.get(path, headers=headers).status_code for path in (USERS, ROLES)] == [200, 200]


@pytest.mark.requirement("WF-ADM-0020-A")
def test_a_role_composed_of_two_actors_gives_its_holder_the_permissions_of_both(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « Un rôle d'habilitation composé sur mesure permet à un utilisateur de cumuler des
    # permissions relevant de deux acteurs différents. » : here, a role composed through the API
    # of a permission of the project manager and one of the administrator, given to an account,
    # makes both its effective permissions; their exercise awaits EP-05.
    assert "planning.write" in PROJECT_MANAGER
    assert "planning.write" not in ADMINISTRATOR
    assert "users.write" in ADMINISTRATOR
    assert "users.write" not in PROJECT_MANAGER
    administrator = person(role(database, "Administration", permissions=ADMINISTRATOR))
    label = "Planificateur administrateur"
    sent: dict[str, object] = {"label": label, "permissions": ["planning.write"]}
    created = api.post(ROLES, headers=administrator, json=sent)
    assert created.status_code == 201
    composed = created.json()["access_role_id"]
    widened = {"label": label, "permissions": ["planning.write", "users.write"], "lock_version": 0}
    assert api.patch(f"{ROLES}/{composed}", headers=administrator, json=widened).status_code == 200
    headers = person()
    assert me(api, headers)["permissions"] == []
    given = {"access_role_ids": [composed], "lock_version": 0}
    attribution = f"{USERS}/{me(api, headers)['user_id']}/access-roles"
    assert api.request("PUT", attribution, headers=administrator, json=given).status_code == 200
    account = me(api, headers)
    assert account["permissions"] == ["users.write", "planning.write"]
    assert account["access_role_labels"] == [label]


@pytest.mark.requirement("WF-ADM-0090-A")
def test_a_permission_withdrawn_from_a_role_deprives_each_of_its_holders_at_once(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « Le retrait d'une permission à un rôle en prive tous ses porteurs sans qu'ils aient à se
    # reconnecter. » Each holder sends the same request with the same token, before and after:
    # before, it passes the evaluation and is refused for its version alone, writing nothing;
    # after, it is refused for the permission. An evaluation kept per account or per token would
    # let it pass (#761).
    administrator = person(role(database, "Administration", permissions=(CONSULT, CHANGE)))
    held = role(database, "Comptes", permissions=("users.read", "users.write"))
    holders = [person(held), person(held)]

    def change_own_account(headers: dict[str, str]) -> tuple[int, str, dict[str, Any]]:
        own = f"{USERS}/{me(api, headers)['user_id']}"
        return refusal(api.patch(own, headers=headers, json={"lock_version": 9}))

    stale = (412, "STALE_LOCK_VERSION", {"expected_lock_version": 0})
    assert [change_own_account(headers) for headers in holders] == [stale, stale]
    withdrawn = {"label": "Comptes", "permissions": ["users.read"], "lock_version": 0}
    assert api.patch(f"{ROLES}/{held}", headers=administrator, json=withdrawn).status_code == 200
    missing = (403, PERMISSION_MISSING, {"missing_permission": "users.write"})
    assert [change_own_account(headers) for headers in holders] == [missing, missing]


# A permission of the administrator, and an action it opens: on the caller's own account, or on
# the roles; the body sent, with the version 0 besides.
DEPRIVED: list[tuple[str, tuple[str, str | None, dict[str, object]]]] = [
    ("users.write", ("PUT", "activation", {"is_active": False})),
    ("users.write", ("PUT", "access-roles", {"access_role_ids": []})),
    # Giving a role is managing the roles (FBS-1.2, WF-ADM-0090, #834).
    ("access_roles.write", ("PUT", "access-roles", {"access_role_ids": []})),
    ("access_roles.write", ("POST", None, {"label": "Pilote", "permissions": []})),
]


@pytest.mark.requirement("WF-ADM-0020-A")
@pytest.mark.parametrize(("withdrawn", "asked_for"), DEPRIVED)
def test_an_administrator_deprived_of_a_permission_is_refused_its_action(
    api: ContractClient,
    database: Database,
    person: Person,
    withdrawn: str,
    asked_for: tuple[str, str | None, dict[str, object]],
) -> None:
    # « Réciproquement, un rôle privé d'une permission empêche l'action correspondante, quel que
    # soit l'acteur auquel l'utilisateur ressemble. » : the delivered administrator, deprived of
    # one permission, is refused the action it opens, the others staying hers.
    kept = tuple(code for code in ADMINISTRATOR if code != withdrawn)
    headers = person(role(database, "Administrateur", permissions=kept, is_predefined=True))
    method, operation, sent = asked_for
    path = ROLES if operation is None else f"{USERS}/{me(api, headers)['user_id']}/{operation}"
    response = api.request(method, path, headers=headers, json={**sent, "lock_version": 0})
    assert refusal(response) == (403, PERMISSION_MISSING, {"missing_permission": withdrawn})
    assert journal(database) == []
    # What she was not deprived of, she does.
    assert api.get(USERS, headers=headers).status_code == 200
    assert api.get(ROLES, headers=headers).status_code == 200


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
    version = {"lock_version": 0}
    unknown = api.request(
        method, f"{ROLES}/{uuid4()}", headers=may_consult, json=sent, params=version
    )
    not_consultable = api.request(
        method, f"{ROLES}/{hidden}", headers=may_not, json=sent, params=version
    )
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


# The operations of the reference, declared router by router, each in its own file (EP-05).
REFERENCE = (
    asked_reference,
    asked_reference_settings,
    asked_cost_types,
    asked_hourly_rates,
    asked_org_nodes,
    asked_resource_roles,
    asked_calendars,
    asked_actual_cost_mapping,
)
# The permissions each served operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "getLiveness": (),
    "getInstallation": (),
    "getMe": (),
    "updateMyPreferences": (),
    "putMyAvatar": (),
    "deleteMyAvatar": (),
    "closeMySessions": (),
    "getUserAvatar": (),
    "listPermissions": (),
    "listUsers": ("users.read",),
    "getUser": ("users.read",),
    "createUser": ("users.write",),
    "updateUser": ("users.read", "users.write"),
    "setUserActivation": ("users.read", "users.write"),
    "anonymizeUser": ("users.read", "users.write"),
    "setUserAccessRoles": ("users.read", "users.write", CHANGE),
    "createPasswordSetupLink": ("users.read", "users.write"),
    "resendInvitation": ("users.read", "users.write"),
    "startIdentitySync": ("users.write",),
    "getLatestIdentitySync": ("users.read",),
    "listAccessRoles": (CONSULT,),
    "getAccessRole": (CONSULT,),
    "createAccessRole": (CHANGE,),
    "updateAccessRole": (CONSULT, CHANGE),
    "deleteAccessRole": (CONSULT, CHANGE),
    "listBackgroundTasks": (),
    "getBackgroundTask": (),
    "listAuditEvents": ("audit_log.read",),
    "listAuditFacets": ("audit_log.read",),
    "listBackups": ("backups.read",),
    "startBackup": ("backups.write",),
    "startRestore": ("platform_restore",),
    "getBackup": ("backups.read",),
    "downloadBackup": ("backups.read", "backups.write"),
    "openChunkedUpload": ("platform_restore",),
    "uploadChunk": ("platform_restore",),
    "completeChunkedUpload": ("platform_restore",),
    **{name: asked for router in REFERENCE for name, asked in router.ASKED.items()},
}
# Two files that declare the same operation would overwrite each other in the table above.
DECLARED = [name for router in REFERENCE for name in router.ASKED]
assert len(DECLARED) == len(set(DECLARED)), sorted(
    name for name in set(DECLARED) if DECLARED.count(name) > 1
)
# The permission each list of the reference asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {
    name: permission for router in REFERENCE for name, permission in router.INACTIVE.items()
}


# The operations that ask for no permission and still refuse by a 404 the object their path names:
# the task another account asked for does not exist for the caller, nor the avatar of an account
# without one.
PATH_OBJECTS = {"getBackgroundTask", "getUserAvatar"}


def asked(route: APIRoute) -> tuple[str, ...]:
    """Give the permissions a route asks for, by its dependencies."""
    return tuple(
        permission
        for depends in route.dependencies
        if isinstance(depends.dependency, Requires)
        for permission in depends.dependency.permissions
    )


def inactive(route: APIRoute) -> str | None:
    """Give the permission a route asks for besides to read deactivated objects, if any."""
    return next(
        (
            depends.dependency.permission
            for depends in route.dependencies
            if isinstance(depends.dependency, RequiresForInactive)
        ),
        None,
    )


def served_routes(services: Services) -> dict[str, APIRoute]:
    """Give the routes of the application, by the operation each serves."""
    served: list[BaseRoute] = []
    for included in create_app(services).routes:
        router = getattr(included, "original_router", None)
        served.extend(cast("list[BaseRoute]", router.routes) if router else [included])
    return {
        route.operation_id: route
        for route in served
        if isinstance(route, APIRoute) and route.operation_id
    }


def refused_without(permission: str) -> str:
    """Give the status the evaluation refuses an actor without ``permission`` by."""
    with pytest.raises((NotFoundError, ForbiddenError)) as refused:
        require(Actor(uuid4(), ()), permission)
    return str(refused.value.status)


def test_every_served_operation_asks_for_the_permission_the_contract_refuses_it_without(
    contract: OpenAPI, services: Services
) -> None:
    # A permission to consult missing is a 404, any other a 403: the operation declares the
    # refusal it may give; one that declares neither asks for nothing. An operation that asks for
    # nothing refuses nothing by a 403, nor by a 404 unless it reads an object of its caller's own.
    routes = served_routes(services)
    assert {name: asked(route) for name, route in routes.items()} == ASKED
    declared = operations(contract)
    for name, permissions in ASKED.items():
        method, path = declared[name]
        relative = path.removeprefix((contract.spec / "servers" / 0 / "url").read_value())
        responses = set((contract.spec / "paths" / relative / method.lower() / "responses").keys())
        needed = {refused_without(code) for code in permissions}
        assert needed <= responses, name
        if not permissions:
            refused = {"403"} if name in PATH_OBJECTS else {"403", "404"}
            assert not refused & responses, name


def test_the_roles_held_and_their_permissions_are_read_at_once_deleted_ones_apart(
    api: ContractClient, database: Database, person: Person
) -> None:
    # One reading of both, the roles by label, the permissions in the order of the catalogue, each
    # once (#756); a role that grants nothing is held all the same.
    estimating = role(database, "Chiffreur", permissions=("estimate.write", "estimate.read"))
    reading = role(database, "Lecteur", permissions=("estimate.read", "users.read"))
    deleted = role(database, "Auditeur", permissions=("audit_log.read",), deleted=True)
    empty = role(database, "Aucun", permissions=())
    role(database, "Pilote", permissions=("planning.read",))
    user_id = UUID(me(api, person(reading, deleted, estimating, empty))["user_id"])
    with database.transaction() as session:
        held = holding(session, user_id)
    assert [(each.access_role_id, each.label) for each in held.roles] == [
        (empty, "Aucun"),
        (estimating, "Chiffreur"),
        (reading, "Lecteur"),
    ]
    assert held.permissions == ("users.read", "estimate.read", "estimate.write")


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


@pytest.mark.requirement("WF-REF-0150-A")
def test_every_list_of_the_reference_asks_for_its_permission_to_read_the_deactivated(
    contract: OpenAPI, services: Services
) -> None:
    # A list that reads deactivated objects declares the 403 that refuses them.
    routes = served_routes(services)
    held = {name: inactive(route) for name, route in routes.items()}
    assert {name: permission for name, permission in held.items() if permission} == INACTIVE
    declared = operations(contract)
    for name in INACTIVE:
        method, path = declared[name]
        relative = path.removeprefix((contract.spec / "servers" / 0 / "url").read_value())
        assert "403" in (contract.spec / "paths" / relative / method.lower() / "responses"), name


@pytest.mark.requirement("WF-REF-0150-A")
def test_every_list_that_asks_for_deactivated_objects_checks_its_reading_first(
    services: Services,
) -> None:
    # Placed before ``Requires``, the guard would refuse with a 403 a caller who may not read the
    # part of the reference at all, who must be told 404 by ``Requires``.
    for name, route in served_routes(services).items():
        if name not in INACTIVE:
            continue
        dependencies = [depends.dependency for depends in route.dependencies]
        reading = [i for i, each in enumerate(dependencies) if isinstance(each, Requires)]
        guard = [i for i, each in enumerate(dependencies) if isinstance(each, RequiresForInactive)]
        assert reading, name
        assert len(guard) == 1, name
        assert max(reading) < guard[0], name


def listing(query: str) -> Request:
    """Give a request of a list, with its query."""
    return Request({"type": "http", "method": "GET", "path": "/", "query_string": query.encode()})


@pytest.mark.requirement("WF-REF-0150-A")
@pytest.mark.parametrize(
    "query",
    [
        "include_inactive=true",
        "include_inactive=1",
        "is_active=false",
        # Judged on the request, not on what it would give: ``is_active`` true makes it vain.
        "is_active=true&include_inactive=true",
    ],
)
def test_a_list_that_asks_for_deactivated_objects_is_refused_without_the_permission_naming_it(
    query: str,
) -> None:
    guard = RequiresForInactive("cost_settings.read")
    with pytest.raises(ForbiddenError) as refused:
        guard(listing(query), Actor(uuid4(), ("users.read",)))
    assert (refused.value.status, refused.value.code, dict(refused.value.params)) == (
        403,
        PERMISSION_MISSING,
        {"missing_permission": "cost_settings.read"},
    )
    guard(listing(query), Actor(uuid4(), ("cost_settings.read",)))


@pytest.mark.requirement("WF-REF-0150-A")
@pytest.mark.parametrize(
    "query", ["", "include_inactive=false", "is_active=true", "include_inactive=maybe", "search=x"]
)
def test_a_list_of_the_active_objects_asks_for_no_permission_besides(query: str) -> None:
    # A value that is no boolean is the validation's to refuse, after the evaluation.
    RequiresForInactive("resource_settings.write")(listing(query), Actor(uuid4(), ()))


@pytest.mark.parametrize("part", REFERENCE_PARTS)
def test_the_three_sessions_of_a_part_of_the_reference_hold_none_of_it_its_reading_and_its_change(
    api: ContractClient, reference_sessions: ReferenceSessions, part: str
) -> None:
    sessions = reference_sessions(part)
    every = (sessions.without, sessions.reading, sessions.changing)
    held = [me(api, headers)["permissions"] for headers in every]
    assert held == [[], [f"{part}.read"], [f"{part}.read", f"{part}.write"]]
