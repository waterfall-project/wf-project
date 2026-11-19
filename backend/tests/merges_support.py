# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the merge of a differential applied share (EP-08, US-2560/L2).

A differential of a project costed (``risks_support.costed``) opened through the service
(``amendments_support.opened_amendment``) is merged as the manager does it: its report read, then
confirmed with its two counters and a name of version (``asked``), and its task run by a worker of
the queue of the test (``merged``). The application of the test deposits its tasks in that queue
(``client``); each test module declares its fixtures from these.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from amendments_support import revision_path
from estimate_support import costing
from fastapi.testclient import TestClient
from projects_support import PROJECTS
from projects_support import scene as make_scene
from risks_support import Costed, costed
from sqlalchemy import select, update
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.merge import merge
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from decimal import Decimal

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
REFUSED = "STATE_FORBIDS_OPERATION"
STALE = "STALE_LOCK_VERSION"


def client(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    administration = KeycloakAdmin(keycloak, settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def merging_worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the merges."""
    queue.prepare()
    return Worker(database, queue, {"structure_merge": merge}, "worker", AT_ONCE)


def costed_project(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> Costed:
    """Give the project a fresh platform's manager made, costed at 1 000 in its current revision."""
    stage = make_scene(api, owner, database, realm)
    return costed(api, stage, costing(stage.database))


def merge_path(project: Costed, structure_id: object, revision_id: object = None) -> str:
    """Give the path of the merge of a structure, of the current revision unless one is named."""
    revision = project.revision_id if revision_id is None else revision_id
    base = f"{PROJECTS}/{project.project_id}/revisions/{revision}"
    return f"{base}/structures/{structure_id}/merge"


def read_report(
    api: ContractClient, project: Costed, structure_id: object, revision_id: object = None
) -> dict[str, Any]:
    """Read the report of the merge of a differential, which must be given."""
    path = merge_path(project, structure_id, revision_id)
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def confirmation(found: dict[str, Any], name: str = "v2.0", **changed: Any) -> dict[str, Any]:
    """Give the confirmation of a report: confirmed, a name of version, its two counters."""
    return {
        "confirmed": True,
        "version_name": name,
        "main_structure_lock_version": found["main_structure_lock_version"],
        "amendment_lock_version": found["amendment_lock_version"],
        **changed,
    }


def asked(
    api: ContractClient,
    project: Costed,
    structure_id: object,
    revision_id: object = None,
    **changed: Any,
) -> Any:
    """Read the report of a differential and confirm it, as the manager does; give the answer.

    ``changed`` replaces what the confirmation sends; ``who`` among them, the session that asks.
    """
    who = changed.pop("who", project.stage.manager)
    found = read_report(api, project, structure_id, revision_id)
    sent = confirmation(found, **changed)
    return api.post(merge_path(project, structure_id, revision_id), headers=who.headers, json=sent)


def task_of(api: ContractClient, project: Costed, answer: Any) -> dict[str, Any]:
    """Read the background task an answer of 202 names."""
    assert answer.status_code == 202, answer.text
    read = api.get(f"{TASKS}/{answer.json()['task_id']}", headers=project.stage.manager.headers)
    assert read.status_code == 200, read.text
    return read.json()


def merged(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    structure_id: object,
    revision_id: object = None,
    **changed: Any,
) -> dict[str, Any]:
    """Merge a differential through the service and the worker; give its task, ended."""
    answer = asked(api, project, structure_id, revision_id, **changed)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    return task_of(api, project, answer)


def revision_of(api: ContractClient, project: Costed, revision_id: object) -> dict[str, Any]:
    """Read a revision of the project, as the manager does."""
    path = f"{PROJECTS}/{project.project_id}/revisions/{revision_id}"
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def project_of(api: ContractClient, project: Costed) -> dict[str, Any]:
    """Read the project, as its manager does."""
    path = f"{PROJECTS}/{project.project_id}"
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def current_path(project: Costed) -> str:
    """Give the path of the revision the project costed was opened with."""
    return revision_path(project)


def tasks_of(project: Costed, structure_id: object) -> dict[str, tuple[UUID, UUID, str]]:
    """Read the tasks of a structure by their label: their node, their lineage, their state."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(Task.label, Node.id, Node.lineage_id, Task.progress)
            .join(Node, Node.id == Task.node_id)
            .where(Node.structure_id == UUID(str(structure_id)))
        )
        return {label: (node, lineage, progress) for label, node, lineage, progress in rows}


def lines_of(project: Costed, structure_id: object) -> dict[str, EstimateLine]:
    """Read the lines of a structure by their label, around the service."""
    with project.stage.database.transaction() as session:
        rows = session.scalars(
            select(EstimateLine)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == UUID(str(structure_id)))
        ).all()
        session.expunge_all()
        return {row.label: row for row in rows}


def shape_of(project: Costed, structure_id: object) -> dict[UUID, tuple[object, ...]]:
    """Read the nodes of a structure by their lineage, as a merge designates them.

    Each its kind, its label, the lineage of its parent, and the columns a differential designates:
    a task's mode and duration, a line's category, role, figures, subproject and delay of payment.
    """
    with project.stage.database.transaction() as session:
        nodes = session.execute(
            select(Node.id, Node.lineage_id, Node.kind, Node.parent_id).where(
                Node.structure_id == UUID(str(structure_id))
            )
        ).all()
        lineages = {node: lineage for node, lineage, _, _ in nodes}
        named = [node for node, _, _, _ in nodes]
        tasks = {
            row.node_id: (row.label, row.description, row.scheduling_mode, row.duration_value)
            for row in session.scalars(select(Task).where(Task.node_id.in_(named)))
        }
        lines = {
            row.node_id: (
                row.label,
                row.cost_category_id,
                row.resource_role_id,
                row.quantity,
                row.hours,
                row.unit_disbursement,
                row.subproject_id,
                row.payment_delay_days,
            )
            for row in session.scalars(select(EstimateLine).where(EstimateLine.node_id.in_(named)))
        }
    return {
        lineage: (
            kind,
            *(tasks.get(node) or lines[node]),
            None if parent is None else lineages[parent],
        )
        for node, lineage, kind, parent in nodes
    }


def links_of(project: Costed, structure_id: object) -> set[tuple[str, str, str, Decimal, str]]:
    """Read the links of a structure: its predecessor's label, its successor's, its type and lag."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(TaskLink).where(TaskLink.structure_id == UUID(str(structure_id)))
        ).scalars()
        links = list(rows)
        labels = dict(
            session.execute(
                select(Task.node_id, Task.label).where(Task.structure_id == UUID(str(structure_id)))
            ).all()
        )
        return {
            (
                labels[each.predecessor_id],
                labels[each.successor_id],
                each.link_type,
                each.lag_value,
                each.lag_unit,
            )
            for each in links
        }


def put_line(project: Costed, label: str, **values: object) -> None:
    """Write columns of the lines of a label around the service, as a review would."""
    with project.stage.owner.begin() as connection:
        connection.execute(update(EstimateLine).where(EstimateLine.label == label).values(**values))


def structure_row(project: Costed, structure_id: object) -> CostStructure:
    """Read a structure, around the service."""
    with project.stage.database.transaction() as session:
        row = session.get_one(CostStructure, (project.project_id, UUID(str(structure_id))))
        session.expunge(row)
        return row


def revision_row(project: Costed, revision_id: object) -> Revision:
    """Read a revision, around the service."""
    with project.stage.database.transaction() as session:
        row = session.get_one(Revision, UUID(str(revision_id)))
        session.expunge(row)
        return row


def main_of(project: Costed, revision_id: object) -> UUID:
    """Give the main structure of a revision of the project."""
    with project.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.id).where(
                CostStructure.revision_id == UUID(str(revision_id)), CostStructure.kind == "main"
            )
        )
    assert found is not None
    return found


def copy_of(project: Costed, structure_id: object, revision_id: object) -> UUID:
    """Give the structure of a revision that copies another, by its lineage."""
    with project.stage.database.transaction() as session:
        lineage = session.scalar(
            select(CostStructure.lineage_id).where(CostStructure.id == UUID(str(structure_id)))
        )
        found = session.scalar(
            select(CostStructure.id).where(
                CostStructure.revision_id == UUID(str(revision_id)),
                CostStructure.lineage_id == lineage,
            )
        )
    assert found is not None
    return found
