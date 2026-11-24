# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A deposit an import employed stays used when a cascade deletes the import (US-3250/L2b, #4885).

The import goes with the differential it aims at, or with the revision it writes in, by a key in
cascade (US-3060): neither ``abandonImport`` nor the purge runs, yet the deposit must not read
unused again — not for ``openImport``, which refuses it (404) without reading the storage, nor for
the bound of twenty pending deposits of an account (WF-DAT-0120, US-3250).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import listed, on, opened_amendment, structures_path
from estimate_import_support import entry_of, row, workbook
from estimate_support import costing
from fastapi.testclient import TestClient
from imports_trial import deposited, import_worker, open_import, path, read, run
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed
from sqlalchemy import func, select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.interface import differential_base
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.storage import Bucket
from waterfall.platform.uploads import FileUpload

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Serve the API on the services of the test."""
    client = TestClient(create_app(services), raise_server_exceptions=False)
    return ContractClient(client, contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costing(stage.database))


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def exported(project: Costed, tree: Any) -> bytes:
    """Write the workbook the export writes of a structure, its lines unchanged."""
    items = tree.items()
    lineages = {each["task"]["label"]: each["lineage_id"] for each in items if each["task"]}
    category = entry_of(project.stage.database, CostCategory, project.costs.material)
    lines = {each["estimate_line"]["label"]: each for each in items if each["estimate_line"]}
    rows: list[list[Any]] = []
    for task, label, amount in ((STUDY, "Plans", 600), (MAKING, "Fabrication", 400)):
        details = {
            "Désignation": label,
            "Quantité": 1,
            "Débours unitaire": amount,
            "Délai de paiement (j)": 0,
            "ID ligne": lines[label]["lineage_id"],
        }
        rows.append(row(f"{1 + (task == MAKING)} {task}", category, details))
    tasks = {f"{1 + (task == MAKING)} {task}": lineages[task] for task in (STUDY, MAKING)}
    return workbook(rows, tasks)


def employed(api: ContractClient, project: Costed, worker: Worker, aimed: str | None) -> str:
    """Open an import of an estimate on the main structure or a differential, analyse it."""
    stage = project.stage
    tree = project.tree if aimed is None else on(project.tree, aimed)
    upload_id = deposited(api, stage.manager, exported(project, tree))
    body = {"kind": "estimate", "upload_id": upload_id}
    opened = api.post(
        path(stage),
        headers=stage.manager.headers,
        json=body if aimed is None else {**body, "structure_id": aimed},
    )
    assert opened.status_code == 202, opened.text
    run(worker)
    assert read(api, stage, opened.json()["import_id"])["status"] == "analysed"
    return upload_id


def imports_kept(database: Database) -> int:
    """Count the rows of imports left."""
    with database.transaction() as session:
        return session.scalar(select(func.count()).select_from(ImportReport)) or 0


def expired(database: Database, upload_id: str) -> bool:
    """Tell whether a deposit reads expired now."""
    with database.transaction() as session:
        return session.get_one(FileUpload, UUID(upload_id)).expires_at <= utc_now()


def refused_unread(
    api: ContractClient, stage: Scene, upload_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Open an import on a deposit: it is not found (404), and the storage is not read."""
    reads: list[str] = []
    head = Bucket.head

    def counted(bucket: Bucket, key: str, length: int) -> bytes:
        reads.append(key)
        return head(bucket, key, length)

    monkeypatch.setattr(Bucket, "head", counted)
    again = open_import(api, stage.manager, stage.project["project_id"], upload_id)
    assert again.status_code == 404, again.text
    assert reads == []


def removed_differential(api: ContractClient, project: Costed, aimed: str) -> None:
    """Abandon a differential, its base with it."""
    held = next(each for each in listed(api, project) if each["structure_id"] == aimed)
    gone = api.delete(
        f"{structures_path(project)}/{aimed}?lock_version={held['lock_version']}",
        headers=project.stage.manager.headers,
    )
    assert gone.status_code == 204, gone.text


def removed_revision(api: ContractClient, project: Costed) -> None:
    """Abandon the current revision of the project."""
    revision_path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    headers = project.stage.manager.headers
    revision = api.get(revision_path, headers=headers).json()
    gone = api.delete(f"{revision_path}?lock_version={revision['lock_version']}", headers=headers)
    assert gone.status_code == 204, gone.text


def pending(database: Database, stage: Scene) -> int:
    """Count the deposits of the manager that live and that no import names."""
    with database.transaction() as session:
        used = select(ImportReport.upload_id)
        return (
            session.scalar(
                select(func.count()).where(
                    FileUpload.uploaded_by == stage.manager.user_id,
                    FileUpload.expires_at > utc_now(),
                    FileUpload.id.not_in(used),
                )
            )
            or 0
        )


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_deposit_of_an_import_goes_expired_with_the_differential_it_aims_at(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. [US-3250] The differential
    # abandoned takes the import with it by the key; its deposit is no longer free.
    aimed = opened_amendment(api, project)
    upload_id = employed(api, project, worker, aimed)
    held = next(each for each in listed(api, project) if each["structure_id"] == aimed)
    gone = api.delete(
        f"{structures_path(project)}/{aimed}?lock_version={held['lock_version']}",
        headers=project.stage.manager.headers,
    )
    assert gone.status_code == 204, gone.text
    assert imports_kept(database) == 0
    assert expired(database, upload_id)
    assert pending(database, project.stage) == 0
    refused_unread(api, project.stage, upload_id, monkeypatch)


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_deposit_of_an_import_goes_expired_with_the_revision_it_writes_in(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. [US-3250] The revision
    # abandoned takes the import with it by the key; its deposit is no longer free.
    stage = project.stage
    upload_id = employed(api, project, worker, None)
    revision_path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    revision = api.get(revision_path, headers=stage.manager.headers).json()
    gone = api.delete(
        f"{revision_path}?lock_version={revision['lock_version']}", headers=stage.manager.headers
    )
    assert gone.status_code == 204, gone.text
    assert imports_kept(database) == 0
    assert expired(database, upload_id)
    assert pending(database, stage) == 0
    refused_unread(api, stage, upload_id, monkeypatch)


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_deposit_of_an_import_aimed_at_the_base_of_a_differential_goes_expired(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. [US-3250] The import aims
    # at the base, the second of the two structures a differential abandoned holds.
    aimed = opened_amendment(api, project)
    upload_id = employed(api, project, worker, aimed)
    with database.transaction() as session:
        base = differential_base(session, project.project_id, UUID(aimed))
        assert base is not None
        session.execute(update(ImportReport).values(structure_id=base))
    removed_differential(api, project, aimed)
    assert imports_kept(database) == 0
    assert expired(database, upload_id)
    assert pending(database, project.stage) == 0
    refused_unread(api, project.stage, upload_id, monkeypatch)


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_deposit_of_an_import_of_the_project_goes_expired_with_the_revision_it_reads(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. [US-3250] An import of
    # ``scope=project`` has no revision, yet aims at a structure of the revision abandoned: the
    # structure takes it by the key.
    upload_id = employed(api, project, worker, None)
    with database.transaction() as session:
        session.execute(update(ImportReport).values(revision_id=None))
    removed_revision(api, project)
    assert imports_kept(database) == 0
    assert expired(database, upload_id)
    assert pending(database, project.stage) == 0
    refused_unread(api, project.stage, upload_id, monkeypatch)
