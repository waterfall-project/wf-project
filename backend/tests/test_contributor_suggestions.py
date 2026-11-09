# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The accounts the lines of a project propose as its contributors (US-1540, WF-PRJ-0070).

``listContributorSuggestions`` on a project whose manager wrote a labour line through the service
(``nodes_support``, ``estimate_support``): the active accounts attached to the node of a role the
lines of the current revision employ, or of the last marked one, that the list does not count,
each with its node and its roles; ``listContributors`` unchanged until ``setContributors`` is
called. Every answer is checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, mark, opened
from project_rows import STAMP
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import insert, select, update
from support import raw_account

from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.core.users.tables import UserAccount

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MANAGER = "project_manager"
CONTRIBUTOR = "contributor"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def suggestions(api: ContractClient, stage: Scene, who: Any = None) -> list[dict[str, Any]]:
    """Read the suggestions of the project of the stage, as its manager does."""
    headers = (who or stage.manager).headers
    answer = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/contributors/suggestions", headers=headers
    )
    assert answer.status_code == 200, answer.text
    return answer.json()


def listed(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the list of the contributors of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/contributors"
    answer = api.get(path, headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def labour(role: UUID, **line: Any) -> dict[str, Any]:
    """Give a labour line of a role: one person for ten hours, unless said."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": "10", **line}


def node_of(stage: Scene, code: str) -> UUID:
    """Read the node of the organisation of a code."""
    with stage.database.transaction() as session:
        return session.scalars(select(OrgNode.id).where(OrgNode.code == code)).one()


def service(stage: Scene, code: str, role_code: str, costs: Costing) -> tuple[UUID, UUID]:
    """Write a node of the organisation and a role under it; give the node and the role."""
    node, role = uuid4(), uuid4()
    with stage.database.transaction() as session:
        calendar = session.scalars(select(Calendar.id).where(Calendar.is_default)).one()
        session.execute(
            insert(OrgNode).values(
                id=node, code=code, label=f"Service {code}", is_active=True, **STAMP
            )
        )
        session.execute(
            insert(ResourceRole).values(
                id=role,
                code=role_code,
                label=f"Rôle {role_code}",
                org_node_id=node,
                cost_category_id=costs.labour,
                calendar_id=calendar,
                monthly_hours=Decimal(140),
                headcount=Decimal(1),
                is_active=True,
                **STAMP,
            )
        )
    return node, role


def attached(stage: Scene, node: UUID, first_name: str, last_name: str, **columns: Any) -> UUID:
    """Write an account attached to a node of the organisation; give its identifier."""
    row = raw_account(
        first_name=first_name,
        last_name=last_name,
        email=f"{uuid4().hex}@example.org",
        org_node_id=node,
        **{"state": "active", **columns},
    )
    with stage.database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


def a_task(tree: Tree) -> dict[str, Any]:
    """Create a task in the main structure of the revision."""
    return tree.made("Mise en service")


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_the_accounts_of_the_service_of_a_role_employed_are_proposed_with_their_node_and_roles(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Après création d'une ligne de main-d'œuvre portant un rôle relevant d'un service dont aucun
    # utilisateur n'est contributeur, Waterfall propose les utilisateurs de ce service. » The
    # engineers of the service are proposed, by name, each with the node and the roles employed;
    # a deactivated account, an account of another service and a service whose role is not
    # employed are not.
    direction = node_of(stage, "DIR")
    other, unused = service(stage, "ATE", "TECH", costs)
    second_role = add_role_in(stage, direction, "ING2", costs)
    clara = attached(stage, direction, "Clara", "Durand")
    albert = attached(stage, direction, "Albert", "Durand")
    attached(stage, direction, "Zoé", "Absente", state="deactivated")
    attached(stage, other, "Octave", "Ailleurs")
    task = a_task(tree)
    assert suggestions(api, stage) == []
    lines.made(task, **labour(costs.role))
    lines.made(task, **labour(second_role))
    found = suggestions(api, stage)
    assert [item["user_id"] for item in found] == [str(albert), str(clara)]
    assert unused not in {UUID(role) for item in found for role in item["resource_role_ids"]}
    first = found[0]
    assert first["display_name"] == "Albert Durand"
    assert first["is_active"] is True
    assert first["org_node_id"] == str(direction)
    assert first["org_node_label"] == "Direction"
    assert sorted(first["resource_role_labels"]) == ["Ingénieur", "Rôle ING2"]
    assert sorted(first["resource_role_ids"]) == sorted([str(costs.role), str(second_role)])


def add_role_in(stage: Scene, node: UUID, code: str, costs: Costing) -> UUID:
    """Write a role of the labour category under a node, on the default calendar."""
    role = uuid4()
    with stage.database.transaction() as session:
        calendar = session.scalars(select(Calendar.id).where(Calendar.is_default)).one()
        session.execute(
            insert(ResourceRole).values(
                id=role,
                code=code,
                label=f"Rôle {code}",
                org_node_id=node,
                cost_category_id=costs.labour,
                calendar_id=calendar,
                monthly_hours=Decimal(140),
                headcount=Decimal(1),
                is_active=True,
                **STAMP,
            )
        )
    return role


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_each_account_is_proposed_with_the_roles_of_its_own_node_only(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    direction = node_of(stage, "DIR")
    other, technician = service(stage, "ATE", "TECH", costs)
    engineer = attached(stage, direction, "Clara", "Durand")
    mechanic = attached(stage, other, "Octave", "Ailleurs")
    task = a_task(tree)
    lines.made(task, **labour(costs.role))
    lines.made(task, **labour(technician))
    found = {item["user_id"]: item for item in suggestions(api, stage)}
    assert set(found) == {str(engineer), str(mechanic)}
    assert found[str(engineer)]["resource_role_ids"] == [str(costs.role)]
    assert found[str(mechanic)]["resource_role_ids"] == [str(technician)]
    assert found[str(mechanic)]["org_node_label"] == "Service ATE"


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_a_line_that_employs_no_role_proposes_nobody(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    attached(stage, node_of(stage, "DIR"), "Clara", "Durand")
    lines.made(
        a_task(tree),
        quantity="1",
        cost_category_id=str(costs.material),
        unit_disbursement="350.00",
    )
    assert suggestions(api, stage) == []


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_the_contributors_of_the_list_are_not_proposed_and_the_list_is_unchanged_until_confirmed(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Tant que la proposition n'est pas confirmée, la liste est inchangée. » The suggestions
    # are read, twice: the list and its counter are the same; setContributors writes the account,
    # which the proposal then leaves out.
    direction = node_of(stage, "DIR")
    clara = attached(stage, direction, "Clara", "Durand")
    albert = attached(stage, direction, "Albert", "Durand")
    with stage.database.transaction() as session:
        session.execute(
            update(UserAccount)
            .where(UserAccount.id == stage.participant.user_id)
            .values(org_node_id=direction)
        )
    lines.made(a_task(tree), **labour(costs.role))
    before = listed(api, stage)
    first = suggestions(api, stage)
    assert [item["user_id"] for item in first] == [str(albert), str(clara)]
    assert str(stage.participant.user_id) not in {item["user_id"] for item in first}
    suggestions(api, stage)
    assert listed(api, stage) == before
    sent = {
        "contributors": [
            *({"user_id": item["user_id"], "kind": item["kind"]} for item in before["items"]),
            {"user_id": str(clara), "kind": CONTRIBUTOR},
        ],
        "lock_version": before["lock_version"],
    }
    path = f"{PROJECTS}/{stage.project['project_id']}/contributors"
    written = api.put(path, headers=stage.manager.headers, json=sent)
    assert written.status_code == 200, written.text
    assert str(clara) in {item["user_id"] for item in listed(api, stage)["items"]}
    assert [item["user_id"] for item in suggestions(api, stage)] == [str(albert)]


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_the_last_marked_revision_proposes_when_the_project_has_no_current_one(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The current revision is marked: none remains, the lines of the last marked one are read.
    clara = attached(stage, node_of(stage, "DIR"), "Clara", "Durand")
    lines.made(a_task(tree), **labour(costs.role))
    mark(stage, tree.revision)
    assert [item["user_id"] for item in suggestions(api, stage)] == [str(clara)]


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_a_current_revision_without_a_role_proposes_nobody_whatever_the_marked_ones_employed(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    attached(stage, node_of(stage, "DIR"), "Clara", "Durand")
    task = a_task(tree)
    node = lines.made(task, **labour(costs.role))["nodes"][0]
    mark(stage, tree.revision)
    again = Tree(api, stage, opened(api, stage))
    copied = [item for item in again.items() if item["kind"] == "estimate_line"]
    assert len(copied) == 1
    assert node["node_id"] != copied[0]["node_id"]
    assert [item["user_id"] for item in suggestions(api, stage)] != []
    path = f"{again.path}/nodes/{copied[0]['node_id']}?lock_version={copied[0]['lock_version']}"
    removed = api.delete(path, headers=stage.manager.headers)
    assert removed.status_code in {200, 204}, removed.text
    assert suggestions(api, stage) == []


@pytest.mark.requirement("WF-PRJ-0070-A")
def test_the_suggestions_are_read_by_a_participant_and_hidden_from_a_stranger(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    clara = attached(stage, node_of(stage, "DIR"), "Clara", "Durand")
    lines.made(a_task(tree), **labour(costs.role))
    assert [item["user_id"] for item in suggestions(api, stage, stage.participant)] == [str(clara)]
    hidden = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/contributors/suggestions",
        headers=stage.outsider.headers,
    )
    assert (hidden.status_code, hidden.json()["code"]) == (404, "NOT_FOUND")
