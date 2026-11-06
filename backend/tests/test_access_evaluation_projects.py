# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evaluation of an action on a project: the quality of the caller there.

The judgment of ``require_project`` on the permissions and the quality of the actor (contributor,
project manager), the guards ``RequiresProject`` and ``on_project`` on the routes, and the
answers they give, tried on projects and contributors the owner writes and on a route of trial.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from access_rows import role
from fastapi import Depends, FastAPI
from project_rows import insert_project
from pydantic import BaseModel, Field
from realm import KEY, TestRealm
from sqlalchemy import insert
from support import ContractClient, bearer, raw_account

from waterfall.api.evaluation import (
    RequiresProject,
)
from waterfall.core.access_roles.interface import (
    NOT_CONTRIBUTOR,
    NOT_PROJECT_MANAGER,
    PERMISSION_MISSING,
    Actor,
    Standing,
    judge_project,
    require,
    require_project,
)
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.projects.tables import Contributor
from waterfall.core.users.tables import UserAccount
from waterfall.platform.correlation import HEADER
from waterfall.platform.errors import ForbiddenError, NotFoundError

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database

ME = "/api/v1/me"


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


@pytest.mark.requirement("WF-ADM-0110-A")
def test_reading_all_the_projects_missing_is_refused_as_an_unknown_object() -> None:
    # Its code does not end as a reading does: the rule of the suffix refused it by a 403, naming
    # a permission that makes a project exist for the caller (#754).
    with pytest.raises(NotFoundError) as hidden:
        require(Actor(uuid4(), ("project_settings.read",)), "all_projects_read")
    assert (hidden.value.code, dict(hidden.value.params)) == ("NOT_FOUND", {})


READ = "project_settings.read"
WRITE = "project_settings.write"
ALL = "all_projects_read"
HIDDEN: tuple[object, ...] = (404, "NOT_FOUND", {})
NOT_A_CONTRIBUTOR = (403, NOT_CONTRIBUTOR, {"missing_condition": "is_contributor"})
NOT_A_MANAGER = (403, NOT_PROJECT_MANAGER, {"missing_condition": "is_project_manager"})
WRITE_MISSING = (403, PERMISSION_MISSING, {"missing_permission": WRITE})
# What the actor may be on a project: of a project that does not exist, none.
ABSENT = Standing(exists=False, kind=None)
OUTSIDE = Standing(exists=True, kind=None)
CONTRIBUTING = Standing(exists=True, kind="contributor")
MANAGING = Standing(exists=True, kind="project_manager")
BOTH = (READ, WRITE)
# What the actor holds, what it is on the project, what is asked for, and the refusal, if any.
type Judged = tuple[tuple[str, ...], Standing, tuple[str, ...], bool, tuple[object, ...] | None]
JUDGED: dict[str, Judged] = {
    # « Un utilisateur sans la permission de consultation ne voit pas le projet, même
    # contributeur » : 404, whatever its kind, ``all_projects_read`` held or not.
    "no reading, a contributor": ((), CONTRIBUTING, (READ,), False, HIDDEN),
    "no reading, a manager": ((WRITE,), MANAGING, (READ,), False, HIDDEN),
    "no reading, reading all": ((ALL,), OUTSIDE, (READ,), False, HIDDEN),
    # « … un contributeur sans « consulter tous les projets » ne voit que ses projets. »
    "reading, no contributor": ((READ,), OUTSIDE, (READ,), False, HIDDEN),
    "reading, a contributor": ((READ,), CONTRIBUTING, (READ,), False, None),
    "reading all": ((READ, ALL), OUTSIDE, (READ,), False, None),
    # A write is refused alike to whom the project does not exist for, the permission held.
    "writing, no contributor": (BOTH, OUTSIDE, BOTH, False, HIDDEN),
    # To whom may consult it, the permission is named first, then the quality.
    "reading all, no writing": ((READ, ALL), OUTSIDE, BOTH, False, WRITE_MISSING),
    "reading all, writing": ((*BOTH, ALL), OUTSIDE, BOTH, False, NOT_A_CONTRIBUTOR),
    "writing, a contributor": (BOTH, CONTRIBUTING, BOTH, False, None),
    # An action reserved to the project managers: the quality of contributor named before.
    "managing, reading all": ((*BOTH, ALL), OUTSIDE, BOTH, True, NOT_A_CONTRIBUTOR),
    "managing, a contributor": (BOTH, CONTRIBUTING, BOTH, True, NOT_A_MANAGER),
    "managing, a manager": (BOTH, MANAGING, BOTH, True, None),
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » : a project that does not exist, to whom could read it if it did.
    "absent, reading all": ((READ, ALL), ABSENT, (READ,), False, HIDDEN),
    "absent, writing": ((*BOTH, ALL), ABSENT, BOTH, True, HIDDEN),
}


@pytest.mark.requirement("WF-ADM-0110-A")
@pytest.mark.parametrize(
    ("held", "standing", "permissions", "manager", "refused"),
    list(JUDGED.values()),
    ids=list(JUDGED),
)
def test_an_action_on_a_project_is_judged_on_the_permissions_and_the_quality_of_the_actor(
    held: tuple[str, ...],
    standing: Standing,
    permissions: tuple[str, ...],
    manager: bool,
    refused: tuple[object, ...] | None,
) -> None:
    actor = Actor(uuid4(), held)
    if refused is None:
        judge_project(actor, standing, permissions, manager=manager)
        return
    with pytest.raises((NotFoundError, ForbiddenError)) as caught:
        judge_project(actor, standing, permissions, manager=manager)
    assert (caught.value.status, caught.value.code, dict(caught.value.params)) == refused


def a_project(owner: Engine, *contributors: tuple[UUID, str]) -> UUID:
    """Write a project and its contributors as the owner, before any story serves them."""
    project_id = uuid4()
    with owner.begin() as connection:
        connection.execute(insert_project(id=project_id))
        for user_id, kind in contributors:
            row = {"project_id": project_id, "user_account_id": user_id, "kind": kind}
            connection.execute(insert(Contributor).values(**row))
    return project_id


def account_id(api: ContractClient, headers: dict[str, str]) -> UUID:
    """Give the identifier of the account of a caller."""
    return UUID(me(api, headers)["user_id"])


def refused_on(
    session: Session, actor: Actor, project_id: UUID, **manager: bool
) -> tuple[int, str]:
    """Give the status and the code a write of a project is refused by."""
    with pytest.raises((NotFoundError, ForbiddenError)) as caught:
        require_project(session, actor, project_id, READ, WRITE, **manager)
    return caught.value.status, caught.value.code


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_quality_of_each_account_is_read_on_the_project_asked_for_alone(
    api: ContractClient, database: Database, owner: Engine, person: Person
) -> None:
    # The evaluation reads the row of the account on the project asked for, by the module of the
    # projects: a contributor of another project, or of this one in another kind, is not taken
    # for one. « … un contributeur sans « consulter tous les projets » ne voit que ses projets. »
    camille, ines = (account_id(api, person()) for _ in range(2))
    ours = a_project(owner, (camille, "project_manager"), (ines, "contributor"))
    theirs = a_project(owner, (ines, "project_manager"))
    with database.transaction() as session:
        for user_id in (camille, ines):
            require_project(session, Actor(user_id, (READ, WRITE)), ours, READ, WRITE)
        require_project(session, Actor(ines, (READ, WRITE)), theirs, READ, WRITE, manager=True)
        refusals = [
            refused_on(session, Actor(camille, (READ, WRITE)), theirs, manager=True),
            refused_on(session, Actor(ines, (READ, WRITE)), ours, manager=True),
        ]
    assert refusals == [(404, "NOT_FOUND"), (403, NOT_PROJECT_MANAGER)]


@pytest.mark.requirement("WF-ADM-0110-A")
def test_reading_all_the_projects_opens_those_that_exist_and_no_other(
    api: ContractClient, database: Database, owner: Engine, person: Person
) -> None:
    # A project that does not exist is refused as one that may not be consulted, even to whom
    # reads them all: by a 404, a write too, and not by a 403 that would say it exists.
    actor = Actor(account_id(api, person()), (READ, WRITE, ALL))
    project_id = a_project(owner)
    with database.transaction() as session:
        require_project(session, actor, project_id, READ)
        refusals = [refused_on(session, actor, asked_for) for asked_for in (project_id, uuid4())]
    assert refusals == [(403, NOT_CONTRIBUTOR), (404, "NOT_FOUND")]


# The routes of trial of the second term, on a project: a reading, and an action reserved to the
# project managers whose body has a rule of its own. No operation of the contract uses it yet.
PROBE = "/api/v1/projects/{project}/probe"


class Probed(BaseModel):
    """The body of the action of trial: a label, not empty."""

    label: str = Field(min_length=1)


def probing(api: ContractClient) -> TestClient:
    """Give a client of the application, with the routes of trial added to it."""
    app = cast("FastAPI", api.client.app)

    def read() -> dict[str, bool]:
        return {"read": True}

    def change(body: Probed) -> dict[str, str]:
        return {"changed": body.label}

    path = PROBE.format(project="{project_id}")
    reading = RequiresProject(READ)
    app.add_api_route(path, read, methods=["GET"], dependencies=[Depends(reading)])
    managing = RequiresProject(READ, WRITE, manager=True)
    app.add_api_route(path, change, methods=["POST"], dependencies=[Depends(managing)])
    return api.client


@pytest.mark.requirement("WF-ADM-0110-A")
def test_an_unknown_project_and_a_project_not_consultable_get_the_same_answer(
    api: ContractClient, database: Database, owner: Engine, person: Person
) -> None:
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » : the same 404, ``NOT_FOUND``, without a parameter that tells them apart — to whom
    # holds the permission and is no contributor, to a contributor without it, for a project that
    # does not exist, or an identifier that cannot name one.
    client = probing(api)
    reading = person(role(database, "Lecture", permissions=(READ,)))
    contributing = person()
    project_id = a_project(owner, (account_id(api, contributing), "contributor"))
    answers = [
        client.get(PROBE.format(project=project_id), headers=reading),
        client.get(PROBE.format(project=project_id), headers=contributing),
        client.get(PROBE.format(project=uuid4()), headers=reading),
        client.get(PROBE.format(project="PRJ-001"), headers=reading),
    ]
    assert {(answer.status_code, answer.headers["content-type"]) for answer in answers} == {
        (404, "application/problem+json")
    }
    bodies = [answer.json() for answer in answers]
    assert [body.pop("correlation_id") for body in bodies] == [a.headers[HEADER] for a in answers]
    assert bodies == [{"code": "NOT_FOUND", "status": 404}] * len(answers)


@pytest.mark.requirement("WF-ADM-0110-A")
@pytest.mark.requirement("WF-ARC-0070-A")
def test_a_write_on_a_project_is_refused_its_quality_before_its_body_is_validated(
    api: ContractClient, database: Database, owner: Engine, person: Person
) -> None:
    # « Un appel direct à l'API qui tente de modifier […] un projet dont l'utilisateur n'est pas
    # contributeur est refusé, alors même que le front n'en propose pas l'action. » : whom reads
    # all the projects sees it, and is refused its write by 403 ``NOT_CONTRIBUTOR``; a contributor,
    # by 403 ``NOT_PROJECT_MANAGER``; a body that breaks its rule changes neither, and a manager
    # alone reaches the validation, then the action.
    client = probing(api)
    granted = role(database, "Direction", permissions=(READ, WRITE, ALL))
    reader, participant, manager = person(granted), person(granted), person(granted)
    project_id = a_project(
        owner,
        (account_id(api, participant), "contributor"),
        (account_id(api, manager), "project_manager"),
    )
    path = PROBE.format(project=project_id)
    assert client.get(path, headers=reader).json() == {"read": True}
    answers = [
        refusal(client.post(path, headers=headers, json=sent))
        for headers in (reader, participant)
        for sent in ({"label": "Pilote"}, {"label": ""})
    ]
    assert answers == [NOT_A_CONTRIBUTOR] * 2 + [NOT_A_MANAGER] * 2
    invalid = refusal(client.post(path, headers=manager, json={"label": ""}))
    assert invalid[:2] == (422, "VALIDATION_FAILED")
    changed = client.post(path, headers=manager, json={"label": "Pilote"})
    assert changed.json() == {"changed": "Pilote"}
