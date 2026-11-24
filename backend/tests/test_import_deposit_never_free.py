# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A deposit an import employed never becomes free again, abandoned or purged (US-3240b, #4850).

The purge deletes the import an abandonment ended, and with it the only row that named its deposit:
the deposit, which lives to its own term, must not read unused again — neither for ``openImport``
nor for the bound of twenty pending deposits of an account (WF-DAT-0120).
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from imports_trial import (
    ROWS,
    STATE,
    TrialFormat,
    deposited,
    open_import,
    path,
    refusal,
    stand_in,
    trial_file,
    upload,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.interface import purge, remove_purged
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.storage import Bucket
from waterfall.platform.uploads import MOST_PENDING, FileUpload

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

FULL = (409, STATE, {"missing_condition": "pending_uploads_below_limit", "maximum": MOST_PENDING})


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


@pytest.fixture(autouse=True)
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


def abandon(api: ContractClient, stage: Scene, import_id: str) -> Any:
    """Abandon an import as its manager does; give the answer."""
    return api.delete(path(stage, import_id), headers=stage.manager.headers)


def pending(database: Database, stage: Scene) -> int:
    """Count the deposits the manager keeps unexpired, whatever the imports say."""
    with database.transaction() as session:
        return (
            session.scalar(
                select(func.count()).where(
                    FileUpload.uploaded_by == stage.manager.user_id,
                    FileUpload.expires_at > utc_now(),
                )
            )
            or 0
        )


def purged(database: Database, bucket: Bucket) -> None:
    """Run the purge now, and give the storage what it lost."""
    with database.transaction() as session:
        gone = purge(session, utc_now())
    remove_purged(bucket, gone)


def abandoned_deposit(api: ContractClient, stage: Scene) -> str:
    """Deposit a file, open an import on it and abandon it; give the deposit."""
    upload_id = deposited(api, stage.manager, trial_file(*ROWS))
    opening = open_import(api, stage.manager, stage.project["project_id"], upload_id)
    assert opening.status_code == 202, opening.text
    assert abandon(api, stage, opening.json()["import_id"]).status_code == 204
    return upload_id


def freed_again(database: Database, upload_id: str) -> str:
    """Make the deposit of an import abandoned read alive, as an earlier version left it."""
    with database.transaction() as session:
        session.execute(
            update(FileUpload)
            .where(FileUpload.id == UUID(upload_id))
            .values(expires_at=utc_now() + timedelta(hours=20))
        )
    return upload_id


@pytest.mark.requirement("WF-DAT-0120")
def test_an_account_that_abandons_an_import_keeps_its_place_under_the_bound_of_twenty(
    api: ContractClient, stage: Scene, database: Database, backups_bucket: Bucket
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. Twenty deposits, one of
    # them employed then abandoned: it does not count, in the state the abandonment leaves nor
    # after the purge; nineteen are pending, one more fits, the twenty-first is refused.
    manager = stage.manager
    abandoned_deposit(api, stage)
    for _ in range(MOST_PENDING - 1):
        deposited(api, manager, trial_file(*ROWS))
    assert pending(database, stage) == MOST_PENDING - 1
    assert upload(api, manager, trial_file(*ROWS)).status_code == 201
    assert refusal(upload(api, manager, trial_file(*ROWS))) == FULL
    purged(database, backups_bucket)
    assert refusal(upload(api, manager, trial_file(*ROWS))) == FULL


@pytest.mark.requirement("WF-DAT-0120")
def test_the_purge_of_an_abandoned_import_leaves_its_deposit_refused_without_reading_storage(
    api: ContractClient,
    stage: Scene,
    database: Database,
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. The deposit of an import
    # abandoned by an earlier version still lives when the purge deletes the import: the purge
    # expires it in the same transaction, and ``openImport`` refuses it (404) before any read.
    upload_id = freed_again(database, abandoned_deposit(api, stage))
    reads: list[str] = []
    head = Bucket.head

    def counted(bucket: Bucket, key: str, length: int) -> bytes:
        reads.append(key)
        return head(bucket, key, length)

    monkeypatch.setattr(Bucket, "head", counted)
    purged(database, backups_bucket)
    with database.transaction() as session:
        assert session.get(FileUpload, UUID(upload_id)) is None
    again = open_import(api, stage.manager, stage.project["project_id"], upload_id)
    assert again.status_code == 404
    assert reads == []


@pytest.mark.requirement("WF-DAT-0120")
def test_the_bound_does_not_count_a_deposit_whose_import_was_purged(
    api: ContractClient, stage: Scene, database: Database, backups_bucket: Bucket
) -> None:
    # Vérif : un dépôt employé par un import ne redevient jamais libre. Whatever the expiry the
    # deposit of an abandoned import kept, the purge that deletes the import leaves no place taken.
    manager = stage.manager
    freed_again(database, abandoned_deposit(api, stage))
    freed_again(database, abandoned_deposit(api, stage))
    purged(database, backups_bucket)
    assert pending(database, stage) == 0
    for _ in range(MOST_PENDING):
        deposited(api, manager, trial_file(*ROWS))
    assert refusal(upload(api, manager, trial_file(*ROWS))) == FULL
