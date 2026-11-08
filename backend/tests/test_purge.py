# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of what expired: imports, deposits, exports, history.

Laid by US-1380/L1, the socle of EP-06; US-1420/L2 writes its tests here ("Les tests du back").
The purge is tried on the database and the object storage of the tests, with the imports opened
and analysed through the service, at an instant named: the clock of the purge is an argument, so
that a day goes by without waiting for it. The verb of the worker, its lock and its settings are in
``test_worker_main.py``.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from imports_trial import (
    TrialFormat,
    analysed,
    apply,
    import_worker,
    opened,
    read,
    refusal,
    stored,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import insert, select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.interface import (
    Purged,
    purge,
    register_format,
    remove_purged,
    stored_before,
)
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.storage import Bucket, MissingObjectError
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import (
    LIFETIME,
    SMALLEST_PART,
    Cut,
    FileUpload,
    Opened,
    object_key_of,
    record_upload,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker

# A day and an hour on: every deposit, every report and every export of the tests is past its term.
LATER = timedelta(hours=25)


@pytest.fixture
def services_on_storage(
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
def api(contract: OpenAPI, services_on_storage: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(services_on_storage)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial() -> Iterator[TrialFormat]:
    """Register the format of the tests for the remaining to commit, withdrawn after the test."""
    form = TrialFormat()
    withdrawn = register_format("remaining", form)
    yield form
    withdrawn()


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def purged_at(
    database: Database, bucket: Bucket, moment: datetime, *, removing: Bucket | None = None
) -> Purged:
    """Run the purge as the verb of the worker does at ``moment``, the storage listed first.

    The storage loses what it gave through ``removing`` when it is named: another door on it.
    """
    swept = stored_before(bucket, moment)
    with database.transaction() as session:
        gone = purge(session, moment, swept)
    remove_purged(removing or bucket, gone)
    return gone


def export_task(
    database: Database, key: str | None, finished: datetime, *, consumed: bool = False
) -> UUID:
    """Record a task ``export`` that succeeded at ``finished``, its file under ``key``."""
    task_id = new_id()
    result: dict[str, Any] | None = None
    if key is not None:
        result = {"object_key": key, "filename": "planning.xml", "media_type": "application/xml"}
        result |= {"consumed": True} if consumed else {}
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind="export",
                status="succeeded",
                progress=100,
                payload={},
                result=result,
                requested_by=None,
                correlation_id="test-purge",
                attempts=1,
                submitted_at=finished,
                started_at=finished,
                finished_at=finished,
            )
        )
    return task_id


def result_of(database: Database, task_id: UUID) -> dict[str, Any] | None:
    """Read the result a task keeps."""
    with database.transaction() as session:
        return session.get_one(BackgroundTask, task_id).result


def deposit_row_exists(database: Database, key: str) -> bool:
    """Tell whether a deposit of the object under ``key`` is recorded."""
    with database.transaction() as session:
        return session.scalar(select(FileUpload.id).where(FileUpload.object_key == key)) is not None


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_the_purge_passes_an_expired_report_expired_and_deletes_its_file(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    database: Database,
    backups_bucket: Bucket,
) -> None:
    # « Un compte rendu expiré ne peut plus être appliqué, et son fichier n'est plus sur le
    # stockage objet. » : the report is read expired at once; the purge writes it and deletes the
    # file, never to be applied.
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    assert backups_bucket.size(key) is not None
    purged_at(database, backups_bucket, utc_now() + LATER)
    row = stored(database, import_id)
    assert row.status == "expired"
    assert backups_bucket.size(key) is None
    found = read(api, stage, import_id)
    assert found["status"] == "expired"
    assert refusal(apply(api, stage, import_id))[:2] == (409, "STATE_FORBIDS_OPERATION")


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_the_purge_leaves_a_report_that_is_not_expired_and_its_file(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    database: Database,
    backups_bucket: Bucket,
) -> None:
    # The term of a report is a day after its analysis: before it, nothing is passed or deleted.
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    purged_at(database, backups_bucket, utc_now() + timedelta(hours=1))
    assert stored(database, import_id).status == "analysed"
    assert backups_bucket.size(key) is not None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_the_purge_ends_an_import_whose_task_failed_without_a_trace_and_deletes_its_file(
    api: ContractClient,
    stage: Scene,
    database: Database,
    backups_bucket: Bucket,
) -> None:
    # « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration » : an import
    # read ``failed`` — its attempts spent by a worker stopped each time — and never abandoned
    # keeps its file until the purge (#2479); an import abandoned is left as it is.
    failing = opened(api, stage)["import_id"]
    abandoned = opened(api, stage)["import_id"]
    running = opened(api, stage)["import_id"]
    keys = {each: stored(database, each).object_key for each in (failing, abandoned, running)}
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == stored(database, failing).task_id)
            .values(
                status="failed",
                problem={"code": "TASK_ABANDONED", "status": 500},
                finished_at=utc_now(),
            )
        )
        session.execute(
            update(ImportReport)
            .where(ImportReport.id == UUID(abandoned))
            .values(status="abandoned", expires_at=utc_now())
        )
    purged_at(database, backups_bucket, utc_now())
    ended = stored(database, failing)
    assert (ended.status, ended.expires_at) == ("failed", None)
    assert backups_bucket.size(keys[failing]) is None
    assert stored(database, abandoned).status == "abandoned"
    assert stored(database, running).status == "analysing"
    assert backups_bucket.size(keys[running]) is not None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_the_purge_deletes_the_deposit_expired_and_its_object_but_spares_what_an_import_keeps(
    api: ContractClient,
    stage: Scene,
    database: Database,
    backups_bucket: Bucket,
) -> None:
    # « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration » : the row
    # and the object of a deposit past its term go; the object of a deposit an import has taken up
    # is the import's while it keeps it (#2479), and goes with the import's end.
    import_id = opened(api, stage)["import_id"]
    taken = stored(database, import_id)
    idle = object_key_of(uuid4())
    with database.transaction() as session:
        record_upload(
            session,
            UUID(idle.removeprefix("uploads/")),
            Opened(
                "import",
                "oublie.wft",
                3,
                Cut(SMALLEST_PART, 1),
                idle,
                "unused",
                stage.manager.user_id,
            ),
            utc_now() - LIFETIME,
        )
    backups_bucket.put(idle, b"WF")
    purged_at(database, backups_bucket, utc_now() + LATER)
    assert not deposit_row_exists(database, idle)
    assert not deposit_row_exists(database, taken.object_key)
    assert backups_bucket.size(idle) is None
    assert backups_bucket.size(taken.object_key) is not None
    with database.transaction() as session:
        session.execute(
            update(ImportReport)
            .where(ImportReport.id == taken.id)
            .values(status="abandoned", expires_at=utc_now())
        )
    purged_at(database, backups_bucket, utc_now() + LATER)
    # The import over, nothing keeps the object: the sweep of its prefix deletes it.
    assert backups_bucket.size(taken.object_key) is None


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_purge_aborts_the_deposit_by_parts_left_unfinished(
    stage: Scene, database: Database, backups_bucket: Bucket
) -> None:
    # The deposits of EP-03, by parts, left unfinished: the parts received are freed.
    key = object_key_of(uuid4())
    deposit = backups_bucket.open_parts(key)
    backups_bucket.put_part(key, deposit, 1, b"x" * SMALLEST_PART)
    assert backups_bucket.parts(key, deposit)
    with database.transaction() as session:
        record_upload(
            session,
            UUID(key.removeprefix("uploads/")),
            Opened(
                "external_backup",
                "sauvegarde.tar",
                SMALLEST_PART,
                Cut(SMALLEST_PART, 1),
                key,
                deposit,
                stage.manager.user_id,
            ),
            utc_now() - LIFETIME,
        )
    gone = purged_at(database, backups_bucket, utc_now() + LATER)
    assert (key, deposit) in gone.deposits
    assert not deposit_row_exists(database, key)
    with pytest.raises(MissingObjectError):
        backups_bucket.parts(key, deposit)


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_purge_sweeps_the_old_objects_of_uploads_that_no_row_names(
    stage: Scene, database: Database, backups_bucket: Bucket
) -> None:
    # An object written before its row, the process stopped between the two (#2479): past the life
    # of a deposit it is deleted; younger, it may be about to have its row. One a deposit names
    # stays with its row.
    orphan = object_key_of(uuid4())
    named = object_key_of(uuid4())
    backups_bucket.put(orphan, b"orphan")
    backups_bucket.put(named, b"named")
    with database.transaction() as session:
        record_upload(
            session,
            UUID(named.removeprefix("uploads/")),
            Opened(
                "import",
                "nomme.wft",
                5,
                Cut(SMALLEST_PART, 1),
                named,
                "open",
                stage.manager.user_id,
            ),
            utc_now() + timedelta(hours=48),
        )
    purged_at(database, backups_bucket, utc_now())
    assert backups_bucket.size(orphan) is not None
    purged_at(database, backups_bucket, utc_now() + LATER)
    assert backups_bucket.size(orphan) is None
    assert backups_bucket.size(named) is not None


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_purge_marks_consumed_the_exports_of_more_than_a_day_and_deletes_their_file(
    database: Database, backups_bucket: Bucket
) -> None:
    # « Un export jamais téléchargé disparaît au terme de vingt-quatre heures. » : its file goes and
    # its result is marked consumed, so that the link is dead (404); a younger one, or one already
    # downloaded, is left as it is.
    now = utc_now()
    keys = {each: f"exports/{uuid4()}.xml" for each in ("old", "young", "downloaded")}
    for key in keys.values():
        backups_bucket.put(key, b"<Project/>")
    old = export_task(database, keys["old"], now - timedelta(hours=25))
    young = export_task(database, keys["young"], now - timedelta(hours=23))
    downloaded = export_task(database, keys["downloaded"], now - timedelta(hours=30), consumed=True)
    gone = purged_at(database, backups_bucket, now)
    assert keys["old"] in gone.objects
    assert backups_bucket.size(keys["old"]) is None
    old_result = result_of(database, old)
    assert old_result is not None
    assert old_result["consumed"] is True
    assert old_result["object_key"] == keys["old"]
    young_result = result_of(database, young)
    assert young_result is not None
    assert "consumed" not in young_result
    assert backups_bucket.size(keys["young"]) is not None
    assert result_of(database, downloaded) == {
        "object_key": keys["downloaded"],
        "filename": "planning.xml",
        "media_type": "application/xml",
        "consumed": True,
    }


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_purge_sweeps_the_old_objects_of_exports_that_no_task_names(
    database: Database, backups_bucket: Bucket
) -> None:
    # The object of an export the worker deposited, its transaction then failed (#2484): no task
    # names it, and it goes after a day. One a task whose result is not consumed names stays.
    now = utc_now()
    orphan = f"exports/{uuid4()}.xml"
    named = f"exports/{uuid4()}.xml"
    backups_bucket.put(orphan, b"<Project/>")
    backups_bucket.put(named, b"<Project/>")
    export_task(database, named, now + timedelta(hours=48))
    purged_at(database, backups_bucket, now)
    assert backups_bucket.size(orphan) is not None
    purged_at(database, backups_bucket, now + LATER)
    assert backups_bucket.size(orphan) is None
    assert backups_bucket.size(named) is not None


@pytest.mark.requirement("WF-DAT-0120-A")
def test_a_storage_out_of_reach_leaves_the_deletion_to_the_next_pass_and_ends_nothing(
    database: Database, backups_bucket: Bucket
) -> None:
    # The rows are purged and validated; the objects the storage could not lose are found again by
    # the sweep of their prefix once it answers.
    key = f"exports/{uuid4()}.xml"
    backups_bucket.put(key, b"<Project/>")
    task = export_task(database, key, utc_now() - timedelta(hours=25))
    out_of_reach = Bucket.connect("none", "http://127.0.0.1:9", "us-east-1", "key", "secret")
    purged_at(database, backups_bucket, utc_now(), removing=out_of_reach)
    assert backups_bucket.size(key) is not None
    result = result_of(database, task)
    assert result is not None
    assert result["consumed"] is True
    purged_at(database, backups_bucket, utc_now() + LATER)
    assert backups_bucket.size(key) is None


def test_nothing_to_purge_gives_nothing_to_the_storage(database: Database) -> None:
    with database.transaction() as session:
        assert purge(session, utc_now()) == Purged()
