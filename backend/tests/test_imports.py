# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps, with a format of the tests.

Laid by US-1380/L1, the socle of EP-06; US-1420/L1 writes its tests here ("Les tests du back"). The
mechanics are tried through the service and its worker, on the database, Redis and the object
storage of the tests, with the format of ``imports_trial`` — the deposit, the opening and its
refusals, the analysis, the report read, the application judged again, the abandonment —; the
concurrent and the interrupted applications are in ``test_imports_application.py``.
"""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from imports_trial import (
    PROJECTS,
    ROWS,
    UPLOADS,
    TrialFormat,
    analysed,
    apply,
    commands,
    deposited,
    import_worker,
    nodes,
    open_import,
    opened,
    path,
    read,
    refusal,
    run,
    stand_in,
    stored,
    trial_file,
    upload,
    withdraw,
)
from projects_support import Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import insert, inspect, select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import submit
from waterfall.platform.uploads import FileUpload

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker


@pytest.fixture
def import_services(
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
def api(contract: OpenAPI, import_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(import_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def test_a_file_is_deposited_whole_for_an_import_for_twenty_four_hours(
    api: ContractClient, stage: Scene, backups_bucket: Bucket, database: Database
) -> None:
    content = trial_file(*ROWS)
    response = upload(api, stage.manager, content, filename="reste-à-engager.wft")
    assert response.status_code == 201, response.text
    kept = response.json()
    assert (kept["purpose"], kept["filename"], kept["size_bytes"]) == (
        "import",
        "reste-à-engager.wft",
        len(content),
    )
    assert kept["backup_taken_at"] is None
    uploaded_at = kept["uploaded_at"]
    with database.transaction() as session:
        row = session.get_one(FileUpload, UUID(kept["upload_id"]))
        assert row.expires_at - row.created_at == timedelta(hours=24)
        assert (row.part_count, row.deposit, row.completed_at is not None) == (1, None, True)
        key = row.object_key
    assert key == f"uploads/{kept['upload_id']}"
    assert uploaded_at
    assert backups_bucket.size(key) == len(content)


@pytest.mark.parametrize(
    "refused",
    [
        (b"x" * (10 * 1024**2 + 1), "import", 413, None),
        (trial_file(*ROWS), "external_backup", 422, "/purpose"),
        (b"", "import", 422, "/file"),
    ],
)
def test_a_deposit_refused_writes_nothing(
    api: ContractClient, stage: Scene, refused: tuple[bytes, str, int, str | None]
) -> None:
    # Beyond 10 MiB, 413; a backup is deposited by parts, never here; an empty file is no file.
    content, purpose, status, pointer = refused
    response = upload(api, stage.manager, content, purpose=purpose)
    assert response.status_code == status, response.text
    body = response.json()
    if pointer is None:
        assert body["code"] == "FILE_TOO_LARGE"
    else:
        assert [field["pointer"] for field in body["fields"]] == [pointer]
    with stage.database.transaction() as session:
        assert session.scalars(select(FileUpload)).all() == []


def project_rows(database: Database) -> list[list[dict[str, Any]]]:
    """Read every row of the structures and of the revisions, as the database keeps them."""
    with database.transaction() as session:
        return [
            sorted(
                (
                    {
                        column.key: getattr(row, column.key)
                        for column in inspect(row).mapper.column_attrs
                    }
                    for row in session.scalars(select(table))
                ),
                key=lambda each: str(each["id"]),
            )
            for table in (CostStructure, Revision)
        ]


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_between_the_analysis_and_the_confirmation_no_data_of_the_project_changed(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « Entre l'analyse et la confirmation, aucune donnée du projet n'a changé. » : the analysis
    # reads the file and the structure, and writes the report alone.
    revision = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/revisions",
        headers=stage.manager.headers,
        json={},
    ).json()
    project = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    before = (nodes(database), project_rows(database), project.json()["lock_version"])
    found = opened(api, stage, *ROWS)
    assert (found["status"], found["report"], found["expires_at"]) == ("analysing", None, None)
    assert found["revision_id"] == revision["revision_id"]
    assert found["task"]["kind"] == "import_analysis"
    run(worker)
    found = read(api, stage, found["import_id"])
    assert found["status"] == "analysed"
    assert [each["label"] for each in found["report"]["differences"]] == list(ROWS)
    assert found["task"]["status"] == "succeeded"
    assert commands(found) == {"apply": [], "abandon": []}
    after = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert (nodes(database), project_rows(database), after.json()["lock_version"]) == before


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.usefixtures("trial")
def test_the_report_is_kept_in_codes_and_read_the_same_by_every_reader(
    api: ContractClient, stage: Scene, worker: Worker, realm: TestRealm
) -> None:
    # « Un import fait par un utilisateur en français, relu par un utilisateur en anglais, présente
    # son compte rendu en anglais. » : the report is codes and parameters; the screen words them,
    # whatever the language the reader asks in.
    found = analysed(api, stage, worker)
    reader = person(stage.database, realm, *PROJECT_MANAGER, name="Ava")
    contribute(stage.database, stage.project["project_id"], reader, "contributor")
    in_french = {**stage.manager.headers, "Accept-Language": "fr-FR,fr;q=0.9"}
    in_english = {**reader.headers, "Accept-Language": "en-GB,en;q=0.9"}
    by_french = api.get(path(stage, found["import_id"]), headers=in_french).json()
    by_english = api.get(path(stage, found["import_id"]), headers=in_english).json()
    assert by_english["report"] == by_french["report"] == found["report"]
    (rejected,) = by_english["report"]["rejected"]
    assert rejected == {
        "sheet": None,
        "row": 2,
        "code": "UNKNOWN_TASK",
        "params": {"value": "Inconnue"},
    }
    # No sentence in either language: the screen words the codes.
    assert set(rejected) == {"sheet", "row", "code", "params"}
    assert not {"message", "text", "description", "title"} & set(by_english["report"])


@pytest.mark.usefixtures("trial")
def test_the_imports_are_listed_by_pages_the_latest_opened_first(
    api: ContractClient, stage: Scene
) -> None:
    first = opened(api, stage, "Un")["import_id"]
    second = opened(api, stage, "Deux")["import_id"]
    response = api.get(f"{path(stage)}?limit=1&offset=1", headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["meta"] == {"limit": 1, "offset": 1, "total": 2}
    assert [each["import_id"] for each in page["items"]] == [first]
    whole = api.get(path(stage), headers=stage.manager.headers).json()
    assert [each["import_id"] for each in whole["items"]] == [second, first]
    assert "report" not in whole["items"][0]


@pytest.mark.usefixtures("trial")
def test_an_opening_is_refused_for_a_deposit_unknown_used_or_of_another(
    api: ContractClient, stage: Scene
) -> None:
    project_id = stage.project["project_id"]
    unknown = open_import(api, stage.manager, project_id, str(uuid4()))
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    upload_id = deposited(api, stage.manager, trial_file(*ROWS))
    others = open_import(api, stage.participant, project_id, upload_id)
    assert refusal(others)[:2] == (404, "NOT_FOUND")
    assert open_import(api, stage.manager, project_id, upload_id).status_code == 202
    again = open_import(api, stage.manager, project_id, upload_id)
    assert refusal(again)[:2] == (404, "NOT_FOUND")


@pytest.mark.usefixtures("trial")
def test_an_opening_is_refused_for_a_head_its_format_does_not_recognise(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    upload_id = deposited(api, stage.manager, b"PROJECT XML\n")
    response = open_import(api, stage.manager, stage.project["project_id"], upload_id)
    assert refusal(response) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {"expected_format": "remaining", "expected_version": "1"},
    )
    with database.transaction() as session:
        assert session.scalars(select(ImportReport)).all() == []


@pytest.mark.usefixtures("trial")
def test_an_opening_on_a_backup_deposit_names_the_deposit(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    upload_id = uuid4()
    now = utc_now()
    with database.transaction() as session:
        session.execute(
            insert(FileUpload).values(
                id=upload_id,
                purpose="external_backup",
                filename="sauvegarde.tar",
                size_bytes=10,
                part_size_bytes=5 * 1024**2,
                part_count=1,
                object_key=f"uploads/{upload_id}",
                uploaded_by=stage.manager.user_id,
                created_at=now,
                expires_at=now + timedelta(hours=24),
                completed_at=now,
            )
        )
    response = open_import(api, stage.manager, stage.project["project_id"], str(upload_id))
    assert response.status_code == 422, response.text
    assert response.json()["fields"] == [
        {"pointer": "/upload_id", "code": "UPLOAD_PURPOSE_MISMATCH"}
    ]


@pytest.mark.usefixtures("trial")
def test_an_opening_on_an_unknown_structure_or_with_an_inverted_period_is_refused(
    api: ContractClient, stage: Scene
) -> None:
    project_id = stage.project["project_id"]
    upload_id = deposited(api, stage.manager, trial_file(*ROWS))
    unknown = open_import(api, stage.manager, project_id, upload_id, structure_id=str(uuid4()))
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    inverted = open_import(
        api, stage.manager, project_id, upload_id, period_from="2026-05-31", period_to="2026-05-01"
    )
    assert inverted.status_code == 422, inverted.text
    assert inverted.json()["fields"] == [
        {"pointer": "/period_to", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": "2026-05-31"}}
    ]


@pytest.mark.usefixtures("trial")
def test_an_opening_is_refused_for_the_state_of_the_project_in_the_order_of_the_contract(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm, queue: TaskQueue
) -> None:
    project_id = stage.project["project_id"]
    # Without a current revision, whoever may not create it: the import would (409, not 403).
    lacking = person(
        database,
        realm,
        *(code for code in PROJECT_MANAGER if code != "revisions.write"),
        name="Léa",
    )
    contribute(database, project_id, lacking, "contributor")
    upload_id = deposited(api, lacking, trial_file(*ROWS))
    response = open_import(api, lacking, project_id, upload_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "may_create_revision"},
    )
    # A task that writes in the project: before the permission to create the revision.
    with logging_context(correlation_id="imports-busy"), database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, {"project_id": project_id})
    response = open_import(api, lacking, project_id, upload_id)
    assert refusal(response)[2] == {"missing_condition": "no_background_task_running"}
    # A terminal project, before the deposit is even looked at.
    put_in_state(stage.owner, project_id, "completed")
    response = open_import(api, lacking, project_id, str(uuid4()))
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )


def test_an_opening_is_refused_without_the_permission_of_its_kind_or_the_quality(
    api: ContractClient, stage: Scene, trial: TrialFormat
) -> None:
    project_id = stage.project["project_id"]
    upload_id = deposited(api, stage.outsider, trial_file(*ROWS))
    outside = open_import(api, stage.outsider, project_id, upload_id)
    assert refusal(outside)[:2] == (404, "NOT_FOUND")
    reader_upload = deposited(api, stage.reader, trial_file(*ROWS))
    reading = open_import(api, stage.reader, project_id, reader_upload)
    assert refusal(reading) == (403, "PERMISSION_MISSING", {"missing_permission": trial.permission})


def test_an_opening_is_refused_for_a_condition_of_its_kind(
    api: ContractClient, stage: Scene, trial: TrialFormat
) -> None:
    trial.condition = "project_before_in_progress"
    upload_id = deposited(api, stage.manager, trial_file(*ROWS))
    response = open_import(api, stage.manager, stage.project["project_id"], upload_id)
    assert refusal(response)[2] == {"missing_condition": "project_before_in_progress"}


def test_an_import_of_the_project_keeps_its_period_and_aims_at_no_structure(
    api: ContractClient, stage: Scene, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    form = TrialFormat(scope="project", permission="actual_costs.write")
    stand_in(monkeypatch, "actual_costs", form)
    upload_id = deposited(api, stage.manager, trial_file(*ROWS))
    response = open_import(
        api,
        stage.manager,
        stage.project["project_id"],
        upload_id,
        kind="actual_costs",
        period_from="2026-04-01",
        period_to="2026-04-30",
    )
    assert response.status_code == 202, response.text
    found = response.json()
    assert (found["period_from"], found["period_to"]) == ("2026-04-01", "2026-04-30")
    assert (found["structure_id"], found["revision_id"]) == (None, None)
    run(worker)
    assert apply(api, stage, found["import_id"]).status_code == 202
    run(worker)
    # The target the application gives the format: the import applied, the period it declared, and
    # no revision nor structure.
    target = form.seen[-1]
    assert target.import_id == UUID(found["import_id"])
    assert (target.period_from, target.period_to) == (date(2026, 4, 1), date(2026, 4, 30))
    assert (target.revision_id, target.structure_id) == (None, None)
    assert read(api, stage, found["import_id"])["status"] == "applied"


@pytest.mark.requirement("WF-ARC-0100-A")
def test_an_expired_report_is_read_expired_and_can_no_longer_be_applied(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, trial: TrialFormat
) -> None:
    # « Un compte rendu expiré ne peut plus être appliqué, et son fichier n'est plus sur le
    # stockage objet. » : its expiry judged at the reading; the purge deletes the file (L2).
    del trial
    import_id = analysed(api, stage, worker)["import_id"]
    with database.transaction() as session:
        session.execute(
            update(ImportReport)
            .where(ImportReport.id == UUID(import_id))
            .values(expires_at=utc_now() - timedelta(seconds=1))
        )
    found = read(api, stage, import_id)
    assert found["status"] == "expired"
    assert commands(found) == {"apply": ["import_awaiting_decision"], "abandon": []}
    response = apply(api, stage, import_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "import_awaiting_decision"},
    )
    assert stored(database, import_id).status == "analysed"
    assert api.delete(path(stage, import_id), headers=stage.manager.headers).status_code == 204
    assert stored(database, import_id).status == "analysed"


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_an_import_confirmed_by_whom_lost_the_permission_since_is_refused_its_file_deleted(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution
    # n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le
    # stockage objet. » : the application judges its requester again; the import is refused.
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    withdraw(database, stage.manager, "remaining.write")
    response = apply(api, stage, import_id)
    assert refusal(response) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "remaining.write"},
    )
    row = stored(database, import_id)
    assert (row.status, row.expires_at) == ("refused", None)
    assert backups_bucket.size(key) is None
    found = api.get(path(stage, import_id), headers=stage.participant.headers).json()
    assert found["status"] == "refused"
    assert commands(found) == {"apply": ["import_awaiting_decision"], "abandon": []}
    assert api.delete(path(stage, import_id), headers=stage.participant.headers).status_code == 204


@pytest.mark.usefixtures("trial")
def test_the_refusal_of_another_account_leaves_the_import_awaiting_its_decision(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    import_id = analysed(api, stage, worker)["import_id"]
    withdraw(database, stage.participant, "remaining.write")
    response = apply(api, stage, import_id, stage.participant)
    assert refusal(response)[:2] == (403, "PERMISSION_MISSING")
    assert stored(database, import_id).status == "analysed"


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_an_import_whose_project_turned_terminal_since_its_analysis_is_refused(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Il en va de même si le projet est passé dans un état terminal entre-temps. »
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    put_in_state(stage.owner, stage.project["project_id"], "abandoned")
    response = apply(api, stage, import_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    assert stored(database, import_id).status == "refused"
    assert backups_bucket.size(key) is None


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_an_application_refused_during_a_marking_is_asked_again_after_it_without_a_new_deposit(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # « Une application refusée parce qu'un marquage est en cours sur le projet peut être
    # redemandée après lui, sans nouveau dépôt. » : a refusal that passes leaves the report
    # applicable and its file in place (#2475).
    database, queue = worker.database, worker.queue
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    project_id = stage.project["project_id"]
    with logging_context(correlation_id="imports-marking"), database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, {"project_id": project_id})
    response = apply(api, stage, import_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    row = stored(database, import_id)
    assert (row.status, row.expires_at is not None) == ("analysed", True)
    assert backups_bucket.size(key) is not None
    run(worker)
    assert apply(api, stage, import_id).status_code == 202
    assert stored(database, import_id).status == "applying"


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_an_application_by_whom_may_not_create_the_revision_leaves_the_import_awaiting(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # The permission to create the revision the import would create may be granted again: the
    # refusal passes, the import stays ``analysed`` with its file (#2475).
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    withdraw(database, stage.manager, "revisions.write")
    response = apply(api, stage, import_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "may_create_revision"},
    )
    assert stored(database, import_id).status == "analysed"
    assert backups_bucket.size(key) is not None


@pytest.mark.requirement("WF-ARC-0100-A")
def test_an_application_refused_by_a_condition_of_its_kind_refuses_the_import(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket, trial: TrialFormat
) -> None:
    # A condition of the kind — an estimate of the main structure once In progress — does not
    # pass: the import is refused for good, its file deleted (WF-INTF-0100, #2475).
    database = worker.database
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    trial.condition = "project_before_in_progress"
    response = apply(api, stage, import_id)
    assert refusal(response)[2] == {"missing_condition": "project_before_in_progress"}
    assert stored(database, import_id).status == "refused"
    assert backups_bucket.size(key) is None


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_an_application_whose_structure_is_gone_from_the_current_revision_refuses_the_import(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # The revision analysed abandoned, another opened from no marked one: the structure aimed at
    # has no copy there, and the import is refused for good, not found (#2475).
    revision = open_revision(api, stage)
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    revisions = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    abandoned = api.delete(
        f"{revisions}/{revision['revision_id']}?lock_version={revision['lock_version']}",
        headers=stage.manager.headers,
    )
    assert abandoned.status_code == 204, abandoned.text
    open_revision(api, stage)
    assert refusal(apply(api, stage, import_id))[:2] == (404, "NOT_FOUND")
    assert stored(database, import_id).status == "refused"
    assert backups_bucket.size(key) is None


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project as its manager does."""
    response = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/revisions",
        headers=stage.manager.headers,
        json={},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_a_report_that_rejects_the_whole_file_refuses_its_application(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    found = analysed(api, stage, worker, "Câblage", "REFUSE")
    assert commands(found)["apply"] == ["import_file_accepted"]
    response = apply(api, stage, found["import_id"])
    assert refusal(response)[2] == {"missing_condition": "import_file_accepted"}
    assert stored(database, found["import_id"]).status == "refused"


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.usefixtures("trial")
def test_an_abandoned_import_leaves_the_project_unchanged_and_its_file_deleted(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Si l'utilisateur abandonne à cette étape, le projet reste inchangé. » : abandoning is
    # idempotent on an import that ended without writing.
    before = nodes(database)
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    assert backups_bucket.size(key) is not None
    first = api.delete(path(stage, import_id), headers=stage.manager.headers)
    assert first.status_code == 204, first.text
    assert stored(database, import_id).status == "abandoned"
    assert backups_bucket.size(key) is None
    assert nodes(database) == before
    again = api.delete(path(stage, import_id), headers=stage.manager.headers)
    assert again.status_code == 204
    found = read(api, stage, import_id)
    assert (found["status"], commands(found)["apply"]) == (
        "abandoned",
        ["import_awaiting_decision"],
    )


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.usefixtures("trial")
def test_an_import_abandoned_while_analysed_is_not_analysed_after(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    import_id = opened(api, stage, *ROWS)["import_id"]
    assert commands(read(api, stage, import_id))["abandon"] == []
    assert api.delete(path(stage, import_id), headers=stage.manager.headers).status_code == 204
    run(worker)
    row = stored(database, import_id)
    assert (row.status, row.report) == ("abandoned", None)


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.usefixtures("trial")
def test_an_applied_import_cannot_be_abandoned(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    import_id = analysed(api, stage, worker)["import_id"]
    assert apply(api, stage, import_id).status_code == 202
    applying = api.delete(path(stage, import_id), headers=stage.manager.headers)
    assert refusal(applying)[2] == {"missing_condition": "import_not_applied"}
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "applied"
    assert commands(found) == {
        "apply": ["import_awaiting_decision"],
        "abandon": ["import_not_applied"],
    }
    applied = api.delete(path(stage, import_id), headers=stage.manager.headers)
    assert refusal(applied) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "import_not_applied"},
    )


def test_an_analysis_refused_by_its_format_fails_the_import_its_file_deleted(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket, trial: TrialFormat
) -> None:
    trial.analysis = "refuse"
    import_id = opened(api, stage, *ROWS)["import_id"]
    key = stored(stage.database, import_id).object_key
    run(worker)
    found = read(api, stage, import_id)
    assert (found["status"], found["report"], found["expires_at"]) == ("failed", None, None)
    assert found["task"]["problem"]["params"] == {"missing_condition": "task_not_started"}
    assert backups_bucket.size(key) is None


def test_a_deposit_whose_record_fails_leaves_no_object_on_the_storage(
    api: ContractClient, stage: Scene, backups_bucket: Bucket, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The file is written before its row: a row that fails to be kept takes the object away.
    keys: list[str] = []

    def failing(session: Any, upload_id: UUID, *rest: Any) -> None:
        del session, rest
        keys.append(f"uploads/{upload_id}")
        msg = "the record failed"
        raise RuntimeError(msg)

    monkeypatch.setattr("waterfall.api.imports.deposit", failing)
    response = upload(api, stage.manager, trial_file(*ROWS))
    assert response.status_code == 500
    (key,) = keys
    assert backups_bucket.size(key) is None
    with stage.database.transaction() as session:
        assert session.scalars(select(FileUpload)).all() == []


def test_a_file_sent_in_chunks_beyond_the_limit_is_refused_as_it_is_read(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # Without a length announced, the body is counted as it comes: 413, nothing kept.
    boundary = "wf-boundary"
    chunk = b"x" * 1024**2

    def body() -> Iterator[bytes]:
        head = f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nimport\r\n'
        yield head.encode()
        yield (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wft"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        for _ in range(12):
            yield chunk
        yield f"\r\n--{boundary}--\r\n".encode()

    response = api.post(
        UPLOADS,
        headers={
            **stage.manager.headers,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=body(),
    )
    assert response.status_code == 413, response.text
    assert response.json()["code"] == "FILE_TOO_LARGE"
    with database.transaction() as session:
        assert session.scalars(select(FileUpload)).all() == []
