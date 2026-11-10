# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of an import by the worker, with the format of the tests (US-1420/L1).

The task judges the import again as it runs — its requester as it stands then, the state of the
project —, creates the current revision when there is none, and applies in one transaction: an
application refused, broken or interrupted writes nothing of the project. Two applications of one
import at once give one task.
"""

import ast
import inspect
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from imports_trial import (
    PROJECTS,
    ROWS,
    UNREADABLE,
    Stopped,
    TrialFormat,
    analysed,
    apply,
    import_worker,
    nodes,
    opened,
    path,
    read,
    refusal,
    run,
    stand_in,
    stored,
    withdraw,
)
from planning_support import give_a_task
from projects_support import Scene, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import ContractClient, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.contract.models import AuditParams
from waterfall.core.exchanges import judgments
from waterfall.core.exchanges.states import AWAITING_DECISION, FILE_ACCEPTED, apply_lacks
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.history.tables import UndoEntry
from waterfall.core.projects.interface import PROJECT_NOT_TERMINAL
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
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


def revisions(database: Database) -> list[tuple[UUID, str]]:
    """Read every revision of the platform and its status."""
    with database.transaction() as session:
        return sorted(
            (row[0], row[1]) for row in session.execute(select(Revision.id, Revision.status))
        )


def task_of(database: Database, import_id: str) -> BackgroundTask:
    """Read the last task of an import."""
    with database.transaction() as session:
        row = session.get_one(ImportReport, UUID(import_id))
        task = session.get_one(BackgroundTask, row.task_id)
        session.expunge(task)
        return task


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project as its manager does."""
    response = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/revisions",
        headers=stage.manager.headers,
        json={},
    )
    assert response.status_code == 201, response.text
    return response.json()


def marked(api: ContractClient, stage: Scene, worker: Worker, database: Database) -> UUID:
    """Open a revision, give it a task, and mark it by the worker; give it."""
    revision = open_revision(api, stage)
    with database.engine.begin() as connection:
        give_a_task(connection, UUID(revision["revision_id"]))
    marking = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}/mark",
        headers=stage.manager.headers,
        json={"version_name": "Offre v1.0", "lock_version": revision["lock_version"]},
    )
    assert marking.status_code == 202, marking.text
    run(worker)
    return UUID(revision["revision_id"])


@pytest.mark.requirement("WF-INTF-0090-A")
@pytest.mark.usefixtures("trial")
def test_an_import_on_a_project_whose_revisions_are_all_marked_creates_the_current_one(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Un import sur un projet dont toutes les révisions sont marquées crée une révision en cours
    # d'élaboration et s'y applique ; les révisions marquées sont inchangées. »
    first = marked(api, stage, worker, database)
    of_marked = nodes(database)
    found = analysed(api, stage, worker, "Câblage", "Essais")
    assert found["revision_id"] is None
    with database.transaction() as session:
        aimed = session.scalars(
            select(CostStructure).where(CostStructure.id == UUID(found["structure_id"]))
        ).one()
        assert aimed.revision_id == first
    key = stored(database, found["import_id"]).object_key
    response = apply(api, stage, found["import_id"])
    assert response.status_code == 202, response.text
    assert response.json()["kind"] == "import_apply"
    run(worker)
    applied = read(api, stage, found["import_id"])
    assert applied["status"] == "applied", applied
    current = UUID(applied["revision_id"])
    assert revisions(database) == sorted([(first, "marked"), (current, "draft")])
    written = [node for node in nodes(database) if node not in of_marked]
    assert {(revision, kind) for revision, _, kind in written} == {(current, "task")}
    # The two tasks of the file, and the one of the marked revision that the new one copies.
    assert len(written) == 3
    assert [node for node in nodes(database) if node[0] == first] == of_marked
    with database.transaction() as session:
        structure = session.scalars(
            select(CostStructure).where(CostStructure.id == UUID(applied["structure_id"]))
        ).one()
        assert (structure.revision_id, structure.lineage_id) == (current, aimed.lineage_id)
    assert backups_bucket.size(key) is None


@pytest.mark.requirement("WF-INTF-0090-A")
@pytest.mark.usefixtures("trial")
def test_only_the_current_revision_is_modified_by_an_import(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « Seule la révision en cours est modifiée : les tâches, les dates et les montants de la
    # révision marquée sont identiques avant et après chaque import. » : the tasks and their dates.
    first = marked(api, stage, worker, database)
    current = UUID(open_revision(api, stage)["revision_id"])
    of_marked = [node for node in nodes(database) if node[0] == first]
    found = analysed(api, stage, worker)
    assert found["revision_id"] == str(current)
    assert apply(api, stage, found["import_id"]).status_code == 202
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "applied"
    assert [node for node in nodes(database) if node[0] == first] == of_marked
    assert {node[0] for node in nodes(database) if node not in of_marked} == {current}


@pytest.mark.usefixtures("trial")
def test_an_applied_import_is_inscribed_in_the_journal_and_not_in_the_undo_history(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    found = analysed(api, stage, worker)
    assert apply(api, stage, found["import_id"]).status_code == 202
    run(worker)
    applied = read(api, stage, found["import_id"])
    with database.transaction() as session:
        (entry,) = session.scalars(select(AuditEntry).where(AuditEntry.action == "import_apply"))
        assert (entry.object_kind, entry.object_id, entry.object_label) == (
            "import",
            UUID(found["import_id"]),
            found["filename"],
        )
        assert (entry.object_revision_id, entry.params) == (
            UUID(applied["revision_id"]),
            {"import_kind": "remaining"},
        )
        assert entry.actor_user_id == stage.manager.user_id
        assert session.scalars(select(UndoEntry)).all() == []
    read_back = AuditParams.model_validate(entry.params)
    assert read_back.model_dump(mode="json", exclude_unset=True) == entry.params


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_a_permission_withdrawn_before_the_task_runs_refuses_the_import_naming_it(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution
    # n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le
    # stockage objet. » : the task judges the requester again as he stands when it runs.
    before = (nodes(database), revisions(database))
    found = analysed(api, stage, worker)
    key = stored(database, found["import_id"]).object_key
    assert apply(api, stage, found["import_id"]).status_code == 202
    withdraw(database, stage.manager, "remaining.write")
    run(worker)
    task = task_of(database, found["import_id"])
    assert task.status == "failed"
    assert task.problem is not None
    assert (task.problem["code"], task.problem["params"]) == (
        "PERMISSION_MISSING",
        {"missing_permission": "remaining.write"},
    )
    row = stored(database, found["import_id"])
    assert (row.status, row.expires_at, row.applied_at) == ("refused", None, None)
    assert backups_bucket.size(key) is None
    assert (nodes(database), revisions(database)) == before


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("trial")
def test_a_project_turned_terminal_before_the_task_runs_refuses_the_import(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # « Il en va de même si le projet est passé dans un état terminal entre-temps. »
    found = analysed(api, stage, worker)
    key = stored(database, found["import_id"]).object_key
    assert apply(api, stage, found["import_id"]).status_code == 202
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    run(worker)
    task = task_of(database, found["import_id"])
    assert task.problem is not None
    assert task.problem["params"] == {"missing_condition": "project_not_terminal"}
    assert stored(database, found["import_id"]).status == "refused"
    assert backups_bucket.size(key) is None
    assert revisions(database) == []


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.requirement("WF-ARC-0100-A")
def test_an_application_interrupted_leaves_the_project_as_it_was_then_runs_again(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, trial: TrialFormat
) -> None:
    # « Si l'import est interrompu pendant son application, le projet revient à son état
    # antérieur. » and « L'interruption de l'application laisse le projet dans son état
    # antérieur. » : the worker is stopped once the format has written; nothing is kept.
    found = analysed(api, stage, worker)
    before = (nodes(database), revisions(database))
    assert apply(api, stage, found["import_id"]).status_code == 202
    trial.application = "stop"
    with pytest.raises(Stopped):
        run(worker)
    assert (nodes(database), revisions(database)) == before
    assert stored(database, found["import_id"]).status == "applying"
    assert read(api, stage, found["import_id"])["status"] == "applying"
    trial.application = None
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "applied"
    assert len(nodes(database)) == len(before[0]) + 2


@pytest.mark.requirement("WF-INTF-0080-A")
def test_an_application_that_breaks_writes_nothing_and_fails_the_import(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket, trial: TrialFormat
) -> None:
    database = stage.database
    found = analysed(api, stage, worker)
    key = stored(database, found["import_id"]).object_key
    before = (nodes(database), revisions(database))
    assert apply(api, stage, found["import_id"]).status_code == 202
    trial.application = "break"
    run(worker)
    applied = read(api, stage, found["import_id"])
    assert (applied["status"], applied["expires_at"]) == ("failed", None)
    assert applied["task"]["problem"]["code"] == "INTERNAL_ERROR"
    assert (nodes(database), revisions(database)) == before
    assert backups_bucket.size(key) is None


@pytest.mark.usefixtures("trial")
def test_an_import_whose_task_failed_unwritten_reads_failed(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # A task whose attempts a stopped worker spent fails without running its handler: the import
    # it leaves applying reads failed, and its report expires no more.
    found = analysed(api, stage, worker)
    assert apply(api, stage, found["import_id"]).status_code == 202
    task_id = stored(database, found["import_id"]).task_id
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == task_id)
            .values(
                status="failed",
                problem={"code": "INTERNAL_ERROR", "status": 500},
                finished_at=BackgroundTask.submitted_at,
            )
        )
    again = read(api, stage, found["import_id"])
    assert (again["status"], again["expires_at"]) == ("failed", None)
    listed = api.get(path(stage), headers=stage.manager.headers).json()["items"]
    assert [each["status"] for each in listed] == ["failed"]


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.parametrize("step", ["analysing", "applying"])
@pytest.mark.usefixtures("trial")
def test_abandoning_an_import_whose_task_failed_unwritten_deletes_its_file(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    backups_bucket: Bucket,
    step: str,
) -> None:
    # The attempts of the task spent by workers stopped, the row still runs and reads failed: its
    # file is deleted once it is abandoned, and abandoning again changes nothing.
    database = stage.database
    if step == "analysing":
        import_id = opened(api, stage, *ROWS)["import_id"]
    else:
        import_id = analysed(api, stage, worker)["import_id"]
        assert apply(api, stage, import_id).status_code == 202
    key = stored(database, import_id).object_key
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == stored(database, import_id).task_id)
            .values(
                status="failed",
                problem={"code": "INTERNAL_ERROR", "status": 500},
                finished_at=BackgroundTask.submitted_at,
            )
        )
    assert stored(database, import_id).status == step
    assert backups_bucket.size(key) is not None
    for _ in range(2):
        assert api.delete(path(stage, import_id), headers=stage.manager.headers).status_code == 204
        row = stored(database, import_id)
        assert (row.status, row.expires_at) == ("failed", None)
        assert backups_bucket.size(key) is None
    assert read(api, stage, import_id)["status"] == "failed"


@pytest.mark.requirement("WF-INTF-0090-A")
def test_an_application_judges_the_structure_of_the_current_revision_not_the_marked_one(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, trial: TrialFormat
) -> None:
    # Analysed on the last marked revision, then the current one created: the format is asked on
    # the copy the current revision holds, where the application will write.
    marked(api, stage, worker, database)
    found = analysed(api, stage, worker)
    current = UUID(open_revision(api, stage)["revision_id"])
    with database.transaction() as session:
        lineage = session.scalars(
            select(CostStructure.lineage_id).where(CostStructure.id == UUID(found["structure_id"]))
        ).one()
        copy = session.scalars(
            select(CostStructure.id).where(
                CostStructure.revision_id == current, CostStructure.lineage_id == lineage
            )
        ).one()
    assert copy != UUID(found["structure_id"])
    assert apply(api, stage, found["import_id"]).status_code == 202
    judged = trial.seen[-1]
    assert (judged.revision_id, judged.structure_id) == (current, copy)
    run(worker)
    applied = read(api, stage, found["import_id"])
    assert (applied["status"], applied["structure_id"]) == ("applied", str(copy))


@pytest.mark.requirement("WF-INTF-0080-A")
def test_an_abandonment_waits_for_the_lock_of_the_import_and_the_analysis_then_writes_nothing(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, backups_bucket: Bucket
) -> None:
    # The lock of the import held while the format analyses: the abandonment waits for it, wins,
    # and the analysis, resumed, finds the import abandoned and writes no report.
    entered, release = Event(), Event()

    class Slow(TrialFormat):
        def analyse(self, session: Session, target: Any, content: bytes) -> Any:
            entered.set()
            assert release.wait(20)
            return super().analyse(session, target, content)

    patched = pytest.MonkeyPatch()
    stand_in(patched, "remaining", Slow())
    try:
        import_id = opened(api, stage, *ROWS)["import_id"]
        key = stored(database, import_id).object_key
        with ThreadPoolExecutor(2) as others, Session(database.engine) as holding:
            analysis = others.submit(run, worker)
            assert entered.wait(20)
            holding.execute(
                select(ImportReport.id).where(ImportReport.id == UUID(import_id)).with_for_update()
            )
            abandonment = others.submit(
                api.delete, path(stage, import_id), headers=stage.manager.headers
            )
            wait_for_a_lock(database, 1)
            assert not abandonment.done()
            holding.commit()
            assert abandonment.result(timeout=20).status_code == 204
            release.set()
            analysis.result(timeout=20)
    finally:
        release.set()
        patched.undo()
    row = stored(database, import_id)
    assert (row.status, row.report, row.analysed_at) == ("abandoned", None, None)
    assert backups_bucket.size(key) is None


def test_the_file_is_read_before_the_application_takes_a_lock_then_applied_under_them(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The format prepares the file holding no lock (#2582, #2739): while it reads, another
    # transaction takes at once the locks the application takes after — of the import, of the
    # project —, and the application, resumed, writes what the file brings.
    entered, release = Event(), Event()

    class Slow(TrialFormat):
        def prepare(self, content: bytes) -> list[str]:
            entered.set()
            assert release.wait(20)
            return super().prepare(content)

    stand_in(monkeypatch, "remaining", Slow())
    found = analysed(api, stage, worker)
    before = len(nodes(database))
    assert apply(api, stage, found["import_id"]).status_code == 202
    try:
        with ThreadPoolExecutor(1) as others:
            application = others.submit(run, worker)
            assert entered.wait(20)
            with Session(database.engine) as holding:
                held = [
                    holding.scalar(
                        select(ImportReport.id)
                        .where(ImportReport.id == UUID(found["import_id"]))
                        .with_for_update(nowait=True)
                    ),
                    holding.scalar(
                        select(Project.id)
                        .where(Project.id == UUID(stage.project["project_id"]))
                        .with_for_update(nowait=True)
                    ),
                ]
                holding.commit()
            release.set()
            application.result(timeout=20)
    finally:
        release.set()
    assert held == [UUID(found["import_id"]), UUID(stage.project["project_id"])]
    assert read(api, stage, found["import_id"])["status"] == "applied"
    assert len(nodes(database)) == before + len(ROWS)


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_file_the_format_refuses_at_the_preparation_fails_the_import_unwritten(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket, trial: TrialFormat
) -> None:
    # A file the format no longer reads at the application fails the import as its application
    # did before the preparation (#2582): nothing written, its file deleted, the task naming why.
    database = stage.database
    found = analysed(api, stage, worker)
    key = stored(database, found["import_id"]).object_key
    before = (nodes(database), revisions(database))
    assert apply(api, stage, found["import_id"]).status_code == 202
    trial.preparation = "refuse"
    run(worker)
    applied = read(api, stage, found["import_id"])
    assert (applied["status"], applied["expires_at"]) == ("failed", None)
    assert applied["task"]["problem"]["code"] == UNREADABLE
    assert (nodes(database), revisions(database)) == before
    assert backups_bucket.size(key) is None


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_file_refused_at_the_preparation_of_an_import_refused_again_leaves_it_refused(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat
) -> None:
    # « Il en va de même si le projet est passé dans un état terminal entre-temps. » The refusal
    # of the file waits for the import to be judged again, as when its application read the file
    # under the locks: the project turned terminal refuses the import.
    found = analysed(api, stage, worker)
    assert apply(api, stage, found["import_id"]).status_code == 202
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    trial.preparation = "refuse"
    run(worker)
    task = task_of(stage.database, found["import_id"])
    assert task.problem is not None
    assert task.problem["params"] == {"missing_condition": "project_not_terminal"}
    assert read(api, stage, found["import_id"])["status"] == "refused"


def test_a_preparation_that_breaks_waits_for_the_import_judged_again_then_fails_it(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat
) -> None:
    # Whatever the preparation raises waits for the judgment: an error that is not a refusal of the
    # file, on a project turned terminal meanwhile, leaves the import refused as before (#2582);
    # on a project that stands, it fails the import.
    standing = analysed(api, stage, worker)
    assert apply(api, stage, standing["import_id"]).status_code == 202
    trial.preparation = "break"
    run(worker)
    assert read(api, stage, standing["import_id"])["status"] == "failed"
    trial.preparation = None
    found = analysed(api, stage, worker)
    assert apply(api, stage, found["import_id"]).status_code == 202
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    trial.preparation = "break"
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "refused"


@pytest.mark.usefixtures("trial")
def test_two_applications_of_one_import_at_once_give_one_task(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    found = analysed(api, stage, worker)
    import_id = UUID(found["import_id"])

    def confirm() -> Any:
        return apply(api, stage, found["import_id"])

    with ThreadPoolExecutor(2) as others, Session(database.engine) as holding:
        holding.execute(
            select(ImportReport.id).where(ImportReport.id == import_id).with_for_update()
        )
        answers = [others.submit(confirm), others.submit(confirm)]
        wait_for_a_lock(database, 2)
        holding.commit()
        responses = [answer.result(timeout=20) for answer in answers]
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [202, 409]
    (refused,) = [response for response in responses if response.status_code == 409]
    assert refusal(refused)[2] == {"missing_condition": "import_awaiting_decision"}
    with database.transaction() as session:
        applying = session.scalars(
            select(BackgroundTask).where(BackgroundTask.kind == "import_apply")
        ).all()
    assert len(applying) == 1
    assert stored(database, found["import_id"]).status == "applying"


@pytest.mark.requirement("WF-ARC-0100-A")
def test_the_passing_conditions_are_among_those_the_judgments_name_and_no_other() -> None:
    # « Une condition passagère laisse l'import applicable » (#2475): ``apply_import`` recognises
    # the refusal by the name of its condition. The names ``judge_state`` can raise are read from
    # its source (its ``refused(...)`` calls), those the application of the report adds from
    # ``apply_lacks``: the passing ones are two of them, the others are refused for good, and a
    # future condition of the same name as a passing one would be mistaken for it. The kinds
    # registered judge nothing of the state yet; one that does is to be added here.
    calls = ast.walk(ast.parse(inspect.getsource(judgments.judge_state)))
    state = {
        getattr(judgments, call.args[0].id)
        for call in calls
        if isinstance(call, ast.Call)
        and getattr(call.func, "id", None) == "refused"
        and isinstance(call.args[0], ast.Name)
    }
    assert state == {
        PROJECT_NOT_TERMINAL,
        judgments.NO_BACKGROUND_TASK_RUNNING,
        judgments.MAY_CREATE_REVISION,
    }
    lacking = {*apply_lacks("applied", None), *apply_lacks("analysed", {"refusals": [{}]})}
    assert lacking == {AWAITING_DECISION, FILE_ACCEPTED}
    assert set(judgments.PASSING) == {"no_background_task_running", "may_create_revision"}
    assert set(judgments.PASSING) <= state
    assert not set(judgments.PASSING) & ({PROJECT_NOT_TERMINAL} | lacking)
