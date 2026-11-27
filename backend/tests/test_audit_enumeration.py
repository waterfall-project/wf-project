# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The enumeration of WF-SEC-0030 walked, action by action, on the service (US-2980/L3).

« Chacune des actions énumérées produit une inscription datée et attribuée » : the enumeration is
that of the contract (``AuditAction``), and each of its actions is either done here through the
service — the routes and the worker, then read by ``listAuditEvents`` as a reader of the journal
does —, or named in ``ELSEWHERE`` with the test that does it and reads its inscription, which
this file finds in its module. The abandonment of a revision and the deletion of a role, which the
requirement names, are walked here. An action added to the contract is in neither until it is put
in one: the walk fails, naming it.
"""

import ast
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import pytest
from audit_writers import contract_actions
from fastapi.testclient import TestClient
from projects_support import PROJECTS, Scene, create, person
from projects_support import scene as make_scene
from support import ContractClient, nowhere
from test_contributors import CONTRIBUTOR, MANAGER, account

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from uuid import UUID

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

pytestmark = pytest.mark.story("US-2980")

EVENTS = "/api/v1/audit-events"
ROLES = "/api/v1/access-roles"
TESTS = Path(__file__).parent
# The worker takes every task at once.
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
# What an action that this file does not do is tried by: the test that does it, by the service, the
# worker or the function the route calls, and reads the inscription it leaves. The writers of the
# accounts, the roles and the backups are those of ``test_audit_params``, which reads each back
# through the model of the contract, dated and attributed.
PARAMS = (
    "test_audit_params.py",
    "test_each_writer_of_the_journal_inscribes_parameters_the_contract_reads",
)
SCOPE = (
    "test_actual_costs_scope.py",
    "test_an_exclusion_and_a_reinstatement_are_inscribed_in_the_journal_of_audit",
)
ELSEWHERE = {
    "reference_designate": (
        "test_reference_designation.py",
        "test_a_marked_revision_is_designated_the_reference_and_the_designation_is_inscribed",
    ),
    "structure_merge": (
        "test_merges_confirmation.py",
        "test_the_merge_is_inscribed_before_the_marking_and_the_designation_it_produces",
    ),
    "structure_abandon": (
        "test_amendments_abandon.py",
        "test_the_abandonment_is_inscribed_in_the_journal_with_its_structure_and_its_revision",
    ),
    "risk_occurrence": (
        "test_risk_occurrence.py",
        "test_the_occurrence_is_inscribed_in_the_journal",
    ),
    "cost_line_exclude": SCOPE,
    "cost_line_reinstate": SCOPE,
    "import_apply": (
        "test_imports_application.py",
        "test_an_applied_import_is_inscribed_in_the_journal_and_not_in_the_undo_history",
    ),
    "user_create": PARAMS,
    "user_update": PARAMS,
    "user_deactivate": PARAMS,
    "user_reactivate": PARAMS,
    "user_anonymize": PARAMS,
    "password_link_create": PARAMS,
    "user_access_roles_set": PARAMS,
    "backup": PARAMS,
    "restore": PARAMS,
}
# What this file does: the actions of the projects, the revisions and the roles.
WALKED = frozenset(
    {
        "project_create",
        "revision_mark",
        "revision_abandon",
        "project_exit",
        "project_manager_add",
        "project_manager_change",
        "project_manager_remove",
        "access_role_create",
        "access_role_update",
        "access_role_delete",
    }
)


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    _, bucket = nowhere()
    services = Services(database, keycloak, KeycloakAdmin(keycloak, realm_settings), queue, bucket)
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the markings, by the platform's handler."""
    queue.prepare()
    return Worker(database, queue, {"revision_mark": mark}, "worker", AT_ONCE)


def done(response: Any, status: int) -> Any:
    """Give the body of an answer, once its status is the one the contract gives."""
    assert response.status_code == status, response.text
    return response.json() if response.content else None


def journal(api: ContractClient, headers: dict[str, str], actions: str) -> list[dict[str, Any]]:
    """Read, as a reader of the journal does, the inscriptions of these actions, oldest first."""
    query = urlencode({"actions": actions, "sort_order": "asc", "limit": 500})
    return done(api.get(f"{EVENTS}?{query}", headers=headers), 200)["items"]


def put_contributors(
    api: ContractClient,
    stage: Scene,
    project_id: str,
    lines: list[tuple[UUID, str]],
    version: int,
) -> None:
    """Write the whole list of the contributors of a project as the manager of the stage does."""
    body = {
        "contributors": [{"user_id": str(user_id), "kind": kind} for user_id, kind in lines],
        "lock_version": version,
    }
    path = f"{PROJECTS}/{project_id}/contributors"
    done(api.put(path, headers=stage.manager.headers, json=body), 200)


def make_and_delete_a_role(api: ContractClient, headers: dict[str, str]) -> dict[str, Any]:
    """Create a role, change it, delete it, as an administrator does; give the role created."""
    made = done(api.post(ROLES, headers=headers, json={"label": "Pilote", "permissions": []}), 201)
    role = f"{ROLES}/{made['access_role_id']}"
    renamed = {"label": "Pilotage", "permissions": ["planning.read"], "lock_version": 0}
    done(api.patch(role, headers=headers, json=renamed), 200)
    assert api.delete(f"{role}?lock_version=1", headers=headers).status_code == 204
    return made


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_actions_walked_and_those_tried_elsewhere_are_the_enumeration_of_the_contract() -> None:
    # « Chacune des actions énumérées » : none of the contract is left out, none is claimed twice,
    # and no action named here is outside the contract.
    assert not WALKED & set(ELSEWHERE)
    assert WALKED | set(ELSEWHERE) == contract_actions()


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize("action", sorted(ELSEWHERE))
def test_the_test_named_for_an_action_that_is_not_walked_exists_and_spells_it(action: str) -> None:
    # The test is a function of its module, which names the action it reads in the journal.
    module, name = ELSEWHERE[action]
    source = (TESTS / module).read_text(encoding="utf-8")
    functions = {
        node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)
    }
    assert name in functions
    assert f'"{action}"' in source


@pytest.mark.requirement("WF-SEC-0030-A")
def test_each_action_the_service_does_is_inscribed_dated_attributed_and_names_its_object(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, realm: TestRealm
) -> None:
    # « Chacune des actions énumérées produit une inscription datée et attribuée. » « L'abandon
    # d'une révision en cours et la suppression d'un rôle produisent chacun une inscription qui
    # nomme l'action et l'objet. » : each action of ``WALKED`` is done through the routes and the
    # worker, by its author, then read by a reader of the journal: dated between the instants
    # that bound the walk, attributed to its author, naming its object.
    manager, headers, kept = stage.manager, stage.manager.headers, stage.project["project_id"]
    admin = person(database, realm, "access_roles.read", "access_roles.write", name="Alix")
    auditor = person(database, realm, "audit_log.read", name="Ada")
    newcomer = account(database, "Nora", "Blanc")
    before = datetime.now(UTC)
    project = create(api, manager, label="Second projet")
    project_id, base = project["project_id"], f"{PROJECTS}/{project['project_id']}"
    alone = [(manager.user_id, MANAGER)]
    put_contributors(api, stage, project_id, [*alone, (newcomer, MANAGER)], 0)
    put_contributors(api, stage, project_id, [*alone, (newcomer, CONTRIBUTOR)], 1)
    put_contributors(api, stage, project_id, [*alone, (newcomer, MANAGER)], 2)
    put_contributors(api, stage, project_id, alone, 3)
    revisions = f"{base}/revisions"
    marked = done(api.post(revisions, headers=headers, json={}), 201)
    sent = {"version_name": "Offre v1.0", "lock_version": marked["lock_version"]}
    done(api.post(f"{revisions}/{marked['revision_id']}/mark", headers=headers, json=sent), 202)
    assert worker.step()
    opened = done(api.post(revisions, headers=headers, json={}), 201)
    path = f"{revisions}/{opened['revision_id']}?lock_version={opened['lock_version']}"
    assert api.delete(path, headers=headers).status_code == 204
    held = done(api.get(base, headers=headers), 200)["lock_version"]
    leaving = {"to_state": "abandoned", "confirmed": True, "lock_version": held, "reason": "Fin"}
    done(api.post(f"{base}/exit", headers=headers, json=leaving), 200)
    made = make_and_delete_a_role(api, admin.headers)
    after = datetime.now(UTC)
    walked = journal(api, auditor.headers, ",".join(sorted(WALKED)))
    # The project of the stage was created before the walk began, and is inscribed all the same.
    found = [
        event
        for event in walked
        if event["project"] is None or event["project"]["project_id"] != kept
    ]
    assert len(found) == len(walked) - 1
    assert {event["action"] for event in found} == WALKED
    for event in found:
        assert before <= datetime.fromisoformat(event["occurred_at"]) <= after, event["action"]
        who = admin if event["object"]["kind"] == "access_role" else manager
        assert event["actor"]["kind"] == "user"
        assert event["actor"]["user_id"] == str(who.user_id), event["action"]
        assert event["actor"]["display_name"]
    by_action = {event["action"]: event for event in found}
    # The abandonment of a revision and the deletion of a role name the action and the object.
    abandoned = by_action["revision_abandon"]
    assert (abandoned["object"]["kind"], abandoned["object"]["object_id"]) == (
        "revision",
        opened["revision_id"],
    )
    assert abandoned["project"]["project_id"] == project_id
    deleted = by_action["access_role_delete"]
    assert (deleted["object"]["kind"], deleted["object"]["object_id"]) == (
        "access_role",
        made["access_role_id"],
    )
    assert deleted["object"]["label"] == "Pilotage"
    assert by_action["revision_mark"]["object"]["label"] == "Offre v1.0"
    assert by_action["project_create"]["object"]["object_id"] == project_id
    assert by_action["project_exit"]["params"] == {"to_state": "abandoned", "reason": "Fin"}
    # The creator, a project manager by the creation, has no inscription of its own for it
    # (DECISIONS.md, US-2980/L1): the registrations are the newcomer's alone.
    registered = [event for event in found if event["action"].startswith("project_manager")]
    assert {event["object"]["object_id"] for event in registered} == {str(newcomer)}
    assert [event["action"] for event in registered] == [
        "project_manager_add",
        "project_manager_change",
        "project_manager_change",
        "project_manager_remove",
    ]
