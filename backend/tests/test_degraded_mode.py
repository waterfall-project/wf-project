# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The degraded mode of the platform, a component stopped at a time (WF-EXP-0040-A, §4.5.4).

The API runs on the services of the tests with a gate in front of each component it reaches
(``degraded_platform``): stopping a component closes its gate — what it had open is cut, what comes
is refused, as a server that is stopped does — and restoring it opens the gate again, on the same
server, its data as it was. Nothing is replaced in the services: what they do is what the sockets
make them do. The worker is the one of the tests, started when the test says the worker is back.

The three sentences of the Vérif of WF-EXP-0040-A come first, then each line of the table 12
(US-2860); the lines of the directory and of the front are those of the service platform
(``make e2e-service``), which no gate stands in for.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from degraded_platform import Degradable, Servers, build, queue_through, row_counts
from fastapi.testclient import TestClient
from imports_trial import (
    AT_ONCE,
    ROWS,
    TrialFormat,
    deposited,
    import_worker,
    open_import,
    run,
    stand_in,
    trial_file,
    upload,
)
from installed_reference import holding
from metrics_reading import samples, value
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from prometheus_support import TestPrometheus
from redis.exceptions import RedisError
from sqlalchemy import event, select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.contract.models import PlatformComponent
from waterfall.api.status import StatusSources
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.metrics import COMPONENT_UP
from waterfall.platform.prometheus import Prometheus
from waterfall.platform.settings import OperatingParameters
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.backup import BackupTask
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.marking import mark
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

TASKS = "/api/v1/tasks"
BACKUPS = "/api/v1/backups"
SESSIONS = "/api/v1/me/sessions"
PREFERENCES = "/api/v1/me/preferences"
UNAVAILABLE = "COMPONENT_UNAVAILABLE"


class Cutting(KeycloakAdmin):
    """An administration client whose provider stops as the first write reaches it."""

    cut: Any = None

    def _send(self, method: str, path: str, token: str, **options: Any) -> Any:
        if method == "PUT" and self.cut is not None:
            self.cut()
        return super()._send(method, path, token, **options)


@pytest.fixture
def servers(
    realm_settings: ServiceSettings,
    database: Database,
    owner: Engine,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Servers:
    """Give the services of the tests as they are reached directly."""
    return Servers(realm_settings, database, owner, queue, backups_bucket)


@pytest.fixture
def platform(servers: Servers, contract: OpenAPI) -> Iterator[Degradable]:
    """Give the API of the tests with a gate before each component, every one open."""
    made, close = build(servers, contract, Cutting)
    yield made
    close()


@pytest.fixture
def stage(platform: Degradable, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    direct = platform.servers
    return make_scene(platform.api, direct.owner, direct.database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


def refused_naming(response: Any, component: str) -> None:
    """Hold a refusal to be the 503 that names a component of the contract."""
    assert response.status_code == 503, response.text
    problem = response.json()
    assert (problem["code"], problem["params"]) == (UNAVAILABLE, {"component": component})
    assert PlatformComponent(component)


def open_revision(platform: Degradable, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = platform.api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def ask_marking(platform: Degradable, stage: Scene, revision: dict[str, Any]) -> Any:
    """Ask for the marking of a revision, as the manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}/mark"
    sent = {"version_name": "v1.0", "lock_version": revision["lock_version"]}
    return platform.api.post(path, headers=stage.manager.headers, json=sent)


def ask_export(platform: Degradable, stage: Scene, revision: dict[str, Any]) -> Any:
    """Ask for the export of the remaining to commit of a revision, as the manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/exports"
    sent = {"kind": "remaining", "revision_id": revision["revision_id"]}
    return platform.api.post(path, headers=stage.manager.headers, json=sent)


def read_revision(platform: Degradable, stage: Scene, revision_id: str) -> dict[str, Any]:
    """Read a revision of the project of the stage."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision_id}"
    response = platform.api.get(path, headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def read_import(platform: Degradable, stage: Scene, import_id: str) -> dict[str, Any]:
    """Read an import of the project of the stage."""
    path = f"{PROJECTS}/{stage.project['project_id']}/imports/{import_id}"
    response = platform.api.get(path, headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def task_of(platform: Degradable, headers: dict[str, str], task_id: str) -> dict[str, Any]:
    """Follow a task as the one who asked for it does."""
    response = platform.api.get(f"{TASKS}/{task_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def status_of(platform: Degradable, stage: Scene, task_id: str) -> str:
    """Read the status of a task the manager asked for."""
    return task_of(platform, stage.manager.headers, task_id)["status"]


def ended_naming(task: dict[str, Any], component: str) -> None:
    """Hold a task to have failed by the refusal that names a component."""
    assert task["status"] == "failed", task
    problem = task["problem"]
    assert (problem["code"], problem["status"], problem["params"]) == (
        UNAVAILABLE,
        503,
        {"component": component},
    )


def consult_and_enter(platform: Degradable, stage: Scene, label: str) -> None:
    """Consult a project and enter another: what the platform serves while a component is out."""
    api, headers = platform.api, stage.manager.headers
    consulted = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=headers)
    assert consulted.status_code == 200, consulted.text
    entered = api.post(PROJECTS, headers=headers, json={"label": label})
    assert entered.status_code == 201, entered.text


def worker_of(platform: Degradable, databases: dict[str, str]) -> Worker:
    """Give a worker of the queue of the test, which reaches the components as the API does."""
    direct = platform.servers
    direct.queue.prepare()
    imports = ImportTasks(platform.services.backups)
    handlers = {
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "revision_mark": mark,
        "export": ExportTask(platform.services.backups),
        "identity_sync": IdentitySync(platform.services.keycloak_admin),
        "backup": BackupTask(databases, platform.services.backups),
    }
    return Worker(direct.database, direct.queue, handlers, "worker", AT_ONCE)


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
def test_an_import_is_refused_naming_the_object_storage_while_it_is_stopped_and_the_rest_goes_on(
    platform: Degradable, stage: Scene
) -> None:
    # « Pendant l'arrêt du stockage objet, une demande d'import est refusée en nommant le
    # composant, et la consultation comme la saisie continuent. »
    api, manager = platform.api, stage.manager
    project_id = stage.project["project_id"]
    deposit = deposited(api, manager, trial_file(*ROWS))
    before = row_counts(platform.servers.owner)
    platform.stop("object_storage")
    refused_naming(upload(api, manager, trial_file(*ROWS)), "object_storage")
    refused_naming(open_import(api, manager, project_id, deposit), "object_storage")
    # Neither refusal wrote anything: no deposit, no import, no task, no line of the journal.
    assert row_counts(platform.servers.owner) == before
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt")
    platform.restore("object_storage")
    # Nothing was presented as done, and nothing is to be done again but the request itself.
    assert upload(api, manager, trial_file(*ROWS)).status_code == 201
    assert open_import(api, manager, project_id, deposit).status_code == 202


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_marking_asked_while_the_worker_is_stopped_ends_once_it_is_back_with_no_new_request(
    platform: Degradable, stage: Scene
) -> None:
    # « Pendant l'arrêt du worker, un marquage demandé aboutit après le rétablissement, sans
    # nouvelle demande. » No worker runs: the request is accepted, the task waits in the queue
    # while the consultation and the entry go on, and the worker, started, ends it.
    direct = platform.servers
    revision = open_revision(platform, stage)
    asked = ask_marking(platform, stage, revision)
    assert asked.status_code == 202, asked.text
    task_id = asked.json()["task_id"]
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt du worker")
    assert status_of(platform, stage, task_id) == "queued"
    assert direct.queue.waiting() == {UUID(task_id)}
    assert read_revision(platform, stage, revision["revision_id"])["marked_at"] is None
    run(import_worker(direct.database, direct.queue, direct.bucket))
    assert status_of(platform, stage, task_id) == "succeeded"
    marked = read_revision(platform, stage, revision["revision_id"])
    assert (marked["status"], marked["version_name"]) == ("marked", "v1.0")


def stop_at_the_journal(platform: Degradable) -> None:
    """Stop PostgreSQL as the entry of the journal is about to be written: the last of a write."""
    engine = platform.gated_database.engine

    def stop(_connection: Any, _cursor: Any, statement: str, *_rest: Any) -> None:
        if statement.lstrip().startswith(f"INSERT INTO {AuditEntry.__tablename__}"):
            event.remove(engine, "before_cursor_execute", stop)
            platform.stop("database")

    event.listen(engine, "before_cursor_execute", stop)


def stop_as_the_write_commits(platform: Degradable) -> None:
    """Stop Redis as the write commits, before the task it wrote is deposited in the queue."""
    engine = platform.gated_database.engine

    def stop(_connection: Any) -> None:
        platform.stop("cache")

    event.listen(engine, "commit", stop, once=True)


def stop_as_the_object_is_sent(platform: Degradable) -> None:
    """Stop the object storage as the object is sent."""
    events = platform.services.backups.client.meta.events

    def stop(**_given: Any) -> None:
        events.unregister("before-send.s3.PutObject", stop)
        platform.stop("object_storage")

    events.register_first("before-send.s3.PutObject", stop)


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_write_met_by_a_postgresql_that_stops_leaves_no_row_and_is_made_whole_when_it_returns(
    platform: Degradable, stage: Scene
) -> None:
    # « Aucune donnée partiellement écrite ne subsiste après le rétablissement d'un composant
    # tombé en cours d'écriture. » PostgreSQL stops after the rows of a project are written and
    # before its entry of the journal is: the transaction is undone.
    owner, headers = platform.servers.owner, stage.manager.headers
    before = row_counts(owner)
    stop_at_the_journal(platform)
    response = platform.api.post(PROJECTS, headers=headers, json={"label": "Coupé"})
    refused_naming(response, "database")
    platform.restore("database")
    assert row_counts(owner) == before
    again = platform.api.post(PROJECTS, headers=headers, json={"label": "Coupé"})
    assert again.status_code == 201, again.text
    after = row_counts(owner)
    assert {name for name in after if after[name] != before[name]} >= {"project", "audit_entry"}


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_task_written_as_redis_stops_is_not_lost_and_is_taken_when_it_returns(
    platform: Degradable, stage: Scene
) -> None:
    # Redis stops as the task commits: it is written, queued, and not in the stream; the worker
    # that starts once Redis is back deposits again what the table holds, and ends it.
    direct = platform.servers
    revision = open_revision(platform, stage)
    stop_as_the_write_commits(platform)
    asked = ask_marking(platform, stage, revision)
    assert asked.status_code == 202, asked.text
    task_id = asked.json()["task_id"]
    assert status_of(platform, stage, task_id) == "queued"
    assert direct.queue.waiting() == set()
    platform.restore("cache")
    worker = import_worker(direct.database, direct.queue, direct.bucket)
    worker.redeposit()
    run(worker)
    assert status_of(platform, stage, task_id) == "succeeded"
    assert read_revision(platform, stage, revision["revision_id"])["status"] == "marked"


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
def test_a_deposit_met_by_an_object_storage_that_stops_leaves_no_row_and_no_object(
    platform: Degradable, stage: Scene
) -> None:
    direct = platform.servers

    def objects() -> set[str]:
        listed = direct.bucket.client.list_objects_v2(Bucket=direct.bucket.name, Prefix="uploads/")
        return {each.get("Key", "") for each in listed.get("Contents", [])}

    before, kept = row_counts(direct.owner), objects()
    stop_as_the_object_is_sent(platform)
    response = upload(platform.api, stage.manager, trial_file(*ROWS))
    refused_naming(response, "object_storage")
    platform.restore("object_storage")
    assert row_counts(direct.owner) == before
    assert objects() == kept
    assert upload(platform.api, stage.manager, trial_file(*ROWS)).status_code == 201


def subject_of(database: Database, user_id: UUID) -> str:
    """Read the subject an account has in the identity provider."""
    with database.transaction() as session:
        return session.scalars(
            select(UserAccount.idp_subject).where(UserAccount.id == user_id)
        ).one()


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_language_met_by_an_identity_provider_that_stops_is_written_nowhere_until_it_returns(
    platform: Degradable, stage: Scene, realm: TestRealm
) -> None:
    # The provider is told first, Waterfall second: the provider stops as the language reaches
    # it, and the account of Waterfall keeps the language it had; asked again, the change is
    # made in both.
    direct, manager = platform.servers, stage.manager
    subject = subject_of(direct.database, manager.user_id)
    attributes = {"username": "u", "email": "u@example.org", "attributes": {"locale": ["fr"]}}
    realm.accounts = {subject: attributes}
    administration = platform.services.keycloak_admin
    assert isinstance(administration, Cutting)
    administration.cut = lambda: platform.stop("identity_provider")
    before = row_counts(direct.owner)
    asked = {"language": "en"}
    refused = platform.api.patch(PREFERENCES, headers=manager.headers, json=asked)
    refused_naming(refused, "identity_provider")
    assert row_counts(direct.owner) == before
    assert realm.accounts[subject]["attributes"] == {"locale": ["fr"]}
    platform.restore("identity_provider")
    administration.cut = None
    again = platform.api.patch(PREFERENCES, headers=manager.headers, json=asked)
    assert again.status_code == 200, again.text
    assert realm.accounts[subject]["attributes"]["locale"] == ["en"]
    with direct.database.transaction() as session:
        held = session.scalars(
            select(UserAccount.display_preferences).where(UserAccount.id == manager.user_id)
        ).one()
    assert held["language"] == "en"


# Each line of the table 12 (§4.5.4), a component stopped at a time: what continues continues, and
# what stops is refused by the 503 that names the component or, for what a worker does, ends in
# the task by that same problem.


@pytest.mark.story("US-2860")
@pytest.mark.usefixtures("trial")
def test_table_12_postgresql_stopped_the_service_says_so_and_the_dashboard_of_the_operator_goes_on(
    platform: Degradable, stage: Scene
) -> None:
    # PostgreSQL : continue « le tableau de bord de l'exploitant et ses alertes » ; s'arrête
    # « tout ; le service annonce l'indisponibilité au lieu de répondre partiellement ».
    api, manager = platform.api, stage.manager
    project_id = stage.project["project_id"]
    deposit = deposited(api, manager, trial_file(*ROWS))
    platform.stop("database")
    assert api.get("/api/v1/health").json() == {"status": "ok"}
    exposition = api.get("/api/v1/metrics")
    assert exposition.status_code == 200
    assert value(samples(exposition.text), COMPONENT_UP, component="database") == 0
    refused_naming(api.get("/api/v1/health/ready"), "database")
    refused_naming(api.get(f"{PROJECTS}/{project_id}", headers=manager.headers), "database")
    refused_naming(api.post(PROJECTS, headers=manager.headers, json={"label": "Z"}), "database")
    refused_naming(upload(api, manager, trial_file(*ROWS)), "database")
    refused_naming(open_import(api, manager, project_id, deposit), "database")
    platform.restore("database")
    consult_and_enter(platform, stage, "Reprise")
    assert api.get("/api/v1/health/ready").status_code == 200


@pytest.mark.story("US-2860")
@pytest.mark.usefixtures("trial")
def test_table_12_redis_stopped_a_call_with_a_valid_token_goes_on_and_the_tasks_wait_in_the_table(
    platform: Degradable, stage: Scene, databases: dict[str, str]
) -> None:
    # Redis : continue « les appels directs à l'API porteurs d'un jeton d'accès valide » ;
    # s'arrête « la prise de nouvelles tâches, reprises depuis la table des tâches de fond au
    # rétablissement ».
    api, manager = platform.api, stage.manager
    project_id = stage.project["project_id"]
    deposit = deposited(api, manager, trial_file(*ROWS))
    platform.stop("cache")
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt de Redis")
    opened = open_import(api, manager, project_id, deposit)
    assert opened.status_code == 202, opened.text
    assert platform.servers.queue.waiting() == set()
    platform.restore("cache")
    worker = worker_of(platform, databases)
    worker.redeposit()
    run(worker)
    assert read_import(platform, stage, opened.json()["import_id"])["status"] == "analysed"


@pytest.mark.story("US-2860")
def test_table_12_redis_stopped_a_task_the_worker_has_taken_ends_and_is_not_run_again(
    platform: Degradable, stage: Scene
) -> None:
    # Redis : continue « les traitements que le worker a déjà pris ». Redis stops while the marking
    # runs: the task ends in the table, its entry stays pending, and the worker that reads again
    # leaves the task as it is — it ran once.
    direct = platform.servers
    revision = open_revision(platform, stage)
    task_id = ask_marking(platform, stage, revision).json()["task_id"]
    direct.queue.prepare()
    gated = queue_through(direct.queue, platform.gates.cache, timeout=1)

    def stopping(session: Any, task: Any) -> Any:
        platform.stop("cache")
        return mark(session, task)

    taken = Worker(direct.database, gated, {"revision_mark": stopping}, "worker-1", AT_ONCE)
    with pytest.raises(RedisError):
        taken.step()
    gated.close()
    platform.restore("cache")
    assert status_of(platform, stage, task_id) == "succeeded"
    assert direct.queue.waiting() == {UUID(task_id)}
    run(import_worker(direct.database, direct.queue, direct.bucket))
    assert direct.queue.waiting() == set()
    with direct.database.transaction() as session:
        assert session.get_one(BackgroundTask, UUID(task_id)).attempts == 1


@pytest.mark.story("US-2860")
@pytest.mark.usefixtures("trial")
def test_table_12_object_storage_stopped_all_the_rest_goes_on_and_imports_exports_and_backups_stop(
    platform: Degradable, stage: Scene, realm: TestRealm, databases: dict[str, str]
) -> None:
    # Stockage objet : continue « tout le reste » ; s'arrête « les imports, les exports et les
    # sauvegardes » : the first are refused by the 503, the others by the task, which ends by it.
    api, manager = platform.api, stage.manager
    project_id = stage.project["project_id"]
    revision = open_revision(platform, stage)
    deposit = deposited(api, manager, trial_file(*ROWS))
    administrator = holding(platform.servers.database, realm, "backups.read", "backups.write")
    platform.stop("object_storage")
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt du stockage")
    refused_naming(upload(api, manager, trial_file(*ROWS)), "object_storage")
    refused_naming(open_import(api, manager, project_id, deposit), "object_storage")
    exported = ask_export(platform, stage, revision)
    assert exported.status_code == 202, exported.text
    backed_up = api.post(BACKUPS, headers=administrator)
    assert backed_up.status_code == 202, backed_up.text
    run(worker_of(platform, databases))
    ended_naming(task_of(platform, manager.headers, exported.json()["task_id"]), "object_storage")
    ended_naming(task_of(platform, administrator, backed_up.json()["task_id"]), "object_storage")


@pytest.mark.story("US-2860")
@pytest.mark.usefixtures("trial")
def test_table_12_worker_stopped_consulting_and_entering_go_on_and_the_tasks_wait_without_loss(
    platform: Degradable, stage: Scene, realm: TestRealm, databases: dict[str, str]
) -> None:
    # Worker : continue « la consultation et la saisie ; les tâches s'accumulent en file sans
    # perte » ; s'arrête « l'aboutissement des imports, des marquages, des exports et des
    # sauvegardes ». No worker runs: the four are accepted, wait, and end once a worker is there.
    api, manager = platform.api, stage.manager
    project_id = stage.project["project_id"]
    revision = open_revision(platform, stage)
    administrator = holding(platform.servers.database, realm, "backups.read", "backups.write")
    deposit = deposited(api, manager, trial_file(*ROWS))
    opened = open_import(api, manager, project_id, deposit)
    marked = ask_marking(platform, stage, revision)
    exported = ask_export(platform, stage, revision)
    backed_up = api.post(BACKUPS, headers=administrator)
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt du worker")
    assert [r.status_code for r in (opened, marked, exported, backed_up)] == [202] * 4
    asked = [
        (manager.headers, marked.json()["task_id"]),
        (manager.headers, exported.json()["task_id"]),
        (administrator, backed_up.json()["task_id"]),
    ]
    for headers, task_id in asked:
        assert task_of(platform, headers, task_id)["status"] == "queued"
    assert read_import(platform, stage, opened.json()["import_id"])["status"] == "analysing"
    assert len(platform.servers.queue.waiting()) == 4
    run(worker_of(platform, databases))
    for headers, task_id in asked:
        assert task_of(platform, headers, task_id)["status"] == "succeeded"
    assert read_import(platform, stage, opened.json()["import_id"])["status"] == "analysed"


@pytest.mark.story("US-2860")
def test_table_12_identity_provider_stopped_signed_in_callers_go_on_until_their_token_expires(
    platform: Degradable, stage: Scene, realm: TestRealm, databases: dict[str, str]
) -> None:
    # Fournisseur d'identité : continue « les connexions en cours, jusqu'à l'expiration de leur
    # jeton d'accès » ; s'arrête « toute connexion et tout renouvellement de jeton, pour tous les
    # comptes ; la lecture des comptes ».
    api, manager = platform.api, stage.manager
    direct = platform.servers
    subject = subject_of(direct.database, manager.user_id)
    administrator = holding(direct.database, realm, "users.write")
    expired = {"Authorization": f"Bearer {realm.token(subject, 'key-1', lifetime=-1)}"}
    platform.stop("identity_provider")
    consult_and_enter(platform, stage, "Saisie pendant l'arrêt du fournisseur")
    # What the realm itself must do — close the sessions of the account — is refused naming it.
    refused_naming(api.delete(SESSIONS, headers=manager.headers), "identity_provider")
    # The token that expires is refused as expired: the front answers by signing in again.
    gone = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=expired)
    assert (gone.status_code, gone.json()["code"]) == (401, "SESSION_EXPIRED")
    read = api.post("/api/v1/identity-syncs", headers=administrator)
    assert read.status_code == 202, read.text
    run(worker_of(platform, databases))
    ended_naming(task_of(platform, administrator, read.json()["task_id"]), "identity_provider")


@pytest.mark.story("US-2860")
def test_table_12_prometheus_stopped_everything_goes_on_and_the_screen_says_its_metrics_unavailable(
    platform: Degradable, stage: Scene, realm: TestRealm, contract: OpenAPI
) -> None:
    # Prometheus : continue « tout » ; s'arrêtent « les métriques de l'écran d'état et les
    # alertes ».
    metrics = TestPrometheus()
    sources = StatusSources(OperatingParameters(), Prometheus(metrics.address))
    app = create_app(platform.services, sources=sources)
    screen = ContractClient(TestClient(app, raise_server_exceptions=False), contract)
    viewer = holding(platform.servers.database, realm, "system_status.read")
    metrics.stop()
    status = screen.get("/api/v1/system/status", headers=viewer)
    assert status.status_code == 200, status.text
    said = [(each["component"], each["is_available"]) for each in status.json()["components"]]
    assert said == [("metrics", False)]
    consult_and_enter(platform, stage, "Saisie sans Prometheus")
