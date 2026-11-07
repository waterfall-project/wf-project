# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the projects share (US-0920/L1): a platform that lets a project be created.

An installation as its bootstrap leaves it, its reference completed with a category of labour and
a role of resources, and the sessions of the tests of the projects, each the header of a token of
an account of its own: a project manager, a participant who contributes without managing, an
outsider who holds the same permissions on a project it does not contribute to, and a reader who
holds ``all_projects_read``. A project is created through the service by its manager, and put in
a state around it, by the owner of the tables, when only tasks and lines (EP-06, EP-07) could
bring it there.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from access_rows import role
from installed_reference import install
from realm import KEY
from sqlalchemy import insert, select, update
from support import bearer, raw_account

from waterfall.core.access_roles.predefined import MANAGER, PROJECT_MANAGER
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
)
from waterfall.core.projects.tables import Contributor, Project
from waterfall.core.resource_settings.interface import NodeWrite, create_node
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

PROJECTS = "/api/v1/projects"
# The permissions that give nothing to a project: a participant holds those of a manager.
MANAGING = PROJECT_MANAGER
READING = MANAGER


@dataclass(frozen=True, slots=True)
class Person:
    """A session of a test: the header of its token, and the account behind it."""

    headers: dict[str, str]
    user_id: UUID


@dataclass(frozen=True, slots=True)
class Scene:
    """The platform of a test of the projects and its sessions.

    ``manager`` created ``project``, and manages it; ``participant`` contributes to it without
    managing it; ``outsider`` holds the permissions of a manager and is no contributor of it;
    ``reader`` holds ``all_projects_read`` and is no contributor either.
    """

    database: Database
    owner: Engine
    manager: Person
    participant: Person
    outsider: Person
    reader: Person
    project: dict[str, Any]


def person(database: Database, realm: TestRealm, *permissions: str, name: str = "Claire") -> Person:
    """Write an account that holds one role of ``permissions``, and give its session."""
    account = raw_account(email=f"{uuid4().hex}@example.org", first_name=name)
    held = role(database, f"Rôle {uuid4().hex}", permissions=permissions)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**account))
        session.execute(
            insert(UserAccessRole).values(user_account_id=account["id"], access_role_id=held)
        )
    token = realm.token(str(account["idp_subject"]), KEY)
    return Person(bearer(token), UUID(str(account["id"])))


def complete_reference(database: Database) -> None:
    """Complete the reference the bootstrap leaves: a category of labour and a role under a node."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("MO", "Main-d'œuvre", "labor"), act)
        draft = CostCategoryDraft("MO-001", "Ingénierie", "641001", nature.cost_type_id)
        category = create_cost_category(session, draft, act).cost_category_id
        node = create_node(session, NodeWrite("DIR", "Direction"), act)
        calendar_id = session.scalars(select(Calendar.id).where(Calendar.is_default)).one()
        session.execute(
            insert(ResourceRole).values(
                id=new_id(),
                code="ING",
                label="Ingénieur",
                org_node_id=node.node_id,
                cost_category_id=category,
                calendar_id=calendar_id,
                monthly_hours=Decimal(140),
                headcount=Decimal(2),
                is_active=True,
                created_at=act.at,
                updated_at=act.at,
            )
        )


def create(api: ContractClient, who: Person, **body: Any) -> dict[str, Any]:
    """Create a project through the service as ``who`` does, and give what is answered."""
    response = api.post(PROJECTS, headers=who.headers, json={"label": "Rénovation", **body})
    assert response.status_code == 201, response.text
    return response.json()


def contribute(database: Database, project_id: str, who: Person, kind: str) -> None:
    """Inscribe an account on a project around the service (the contributors are US-0930's)."""
    with database.transaction() as session:
        session.execute(
            insert(Contributor).values(
                project_id=UUID(project_id), user_account_id=who.user_id, kind=kind
            )
        )


def put_in_state(owner: Engine, project_id: str, state: str, **columns: object) -> None:
    """Put a project in a state, as its owner: what a task and a line alone reach by the service."""
    with owner.begin() as connection:
        connection.execute(
            update(Project).where(Project.id == UUID(project_id)).values(state=state, **columns)
        )


def scene(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Make the platform of a test: installed, its reference completed, its sessions, a project."""
    install(owner)
    complete_reference(database)
    manager = person(database, realm, *MANAGING, name="Camille")
    participant = person(database, realm, *MANAGING, name="Inès")
    outsider = person(database, realm, *MANAGING, name="Noé")
    reader = person(database, realm, *READING, name="Dominique")
    project = create(api, manager, label="Modernisation du poste de commande")
    contribute(database, project["project_id"], participant, "contributor")
    return Scene(database, owner, manager, participant, outsider, reader, project)
