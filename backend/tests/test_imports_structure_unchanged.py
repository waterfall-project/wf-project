# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import applies only on the structure its report read (US-3210, #4420).

The analysis keeps the counter of the structure it read, and the application compares it at the
request, then under the lock of the structure when its task runs: a planning of MS Project, an
estimate and a remaining to commit whose structure was written since are refused for good
(``import_structure_unchanged``), their file deleted, nothing written; an extraction of actual costs
is not concerned. Through the service and its worker, each answer checked against the contract.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import analysed as costs_analysed
from actual_costs_import_support import declare, extraction, line, subproject
from actual_costs_import_support import in_progress as costs_in_progress
from estimate_import_support import analysed_import, as_exported, two_tasks
from estimate_import_support import workbook as estimate_workbook
from estimate_support import YEAR, Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import (
    apply,
    commands,
    import_worker,
    read,
    refusal,
    run,
    stored,
)
from nodes_support import Tree, mark, opened
from planning_support import insert_task
from projects_support import Scene, put_in_state
from projects_support import scene as make_scene
from remaining_import_support import Rows, labour, material, row_of
from remaining_import_support import analysed as remaining_analysed
from remaining_import_support import workbook as remaining_workbook
from remaining_support import in_progress
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_calendar_gap import SYNTHETIC, ruled
from test_msproject_import import analysed, corpus, imported, planning, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.resource_settings.tables import Calendar as CalendarRow
from waterfall.core.revisions.tables import CostStructure
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

STATE = "STATE_FORBIDS_OPERATION"
CHANGED = (409, STATE, {"missing_condition": "import_structure_unchanged"})
OUTSIDE = "Hors sous-projet"
# A planning of two tasks, and the same reworked in MS Project: a third task added.
FIRST = planning(task(1, "T1"), task(2, "T2"))
REWORKED = planning(task(1, "T1"), task(2, "T2"), task(3, "T3"))


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
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def planned(api: ContractClient, stage: Scene, worker: Worker) -> Tree:
    """Open the current revision and import the planning of two tasks into it; give its tree."""
    tree = Tree(api, stage, opened(api, stage))
    imported(api, stage, worker, FIRST)
    return tree


def tasks_of(tree: Tree) -> list[str]:
    """Give the labels of the tasks of a structure, sorted."""
    return sorted(item["task"]["label"] for item in tree.items() if item["kind"] == "task")


def counter(stage: Scene, structure_id: str) -> int:
    """Read the counter of a structure as the database keeps it."""
    with stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(structure_id))
        )
    assert found is not None
    return found


def refused_for_good(
    api: ContractClient, stage: Scene, bucket: Bucket, import_id: str, answer: Any
) -> None:
    """Say an application refused because its structure was written: refused, its file gone."""
    key = stored(stage.database, import_id).object_key
    assert refusal(answer) == CHANGED
    assert read(api, stage, import_id)["status"] == "refused"
    assert bucket.size(key) is None


def applied_now(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> None:
    """Confirm the application of an import analysed and run it; it is applied."""
    answer = apply(api, stage, import_id)
    assert answer.status_code == 202, answer.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


def task_problem(database: Database, import_id: str) -> tuple[str, dict[str, Any]]:
    """Give the code and the parameters of the problem the task of an import failed on."""
    with database.transaction() as session:
        row = session.get_one(ImportReport, UUID(import_id))
        found = session.get_one(BackgroundTask, row.task_id)
        assert found.problem is not None
        return found.problem["code"], found.problem["params"]


# --- The scenario of #4420, for the three kinds that write a structure ----------------------------


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_planning_whose_structure_got_a_task_since_its_analysis_is_refused_the_task_kept(
    api: ContractClient, stage: Scene, worker: Worker, costs: Costing, backups_bucket: Bucket
) -> None:
    # « Entre l'analyse et la confirmation, aucune donnée du projet n'a changé. » The scenario of
    # #4420: a planning of MS Project analysed, a task and its line of estimate created by
    # ``createNode``, then ``applyImport``: the task is still there, nothing is written — the
    # reimport would have removed it, absent from the file and not started.
    tree = planned(api, stage, worker)
    found = analysed(api, stage, worker, REWORKED)
    import_id = found["import_id"]
    assert stored(stage.database, import_id).structure_lock_version == counter(
        stage, tree.structure_id
    )
    new = tree.made("Câblage du collègue")
    Lines(tree).made(new, quantity="2", resource_role_id=str(costs.role), hours="10")
    # No command states it in advance: the comparison is made at the request (#4420).
    assert commands(read(api, stage, import_id))["apply"] == []
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))
    assert tasks_of(tree) == ["Câblage du collègue", "T1", "T2"]
    assert [item["parent_id"] for item in tree.items() if item["kind"] == "estimate_line"] == [
        new["node_id"]
    ]


@pytest.mark.requirement("WF-ARC-0100-A")
def test_an_estimate_whose_structure_got_a_task_since_its_analysis_is_refused_its_lines_kept(
    api: ContractClient, stage: Scene, worker: Worker, costs: Costing, backups_bucket: Bucket
) -> None:
    # « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution
    # n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le
    # stockage objet. » : likewise an estimate whose structure was written since the analysis.
    tree = Tree(api, stage, opened(api, stage))
    held = two_tasks(tree, costs, stage)
    content = estimate_workbook(as_exported(held, {"Heures": 12}), held["tasks"])
    import_id = analysed_import(api, stage, worker, content)
    labour = held["labour"]["node_id"]
    before = next(item for item in tree.items() if item["node_id"] == labour)
    tree.made("Réception")
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))
    after = next(item for item in tree.items() if item["node_id"] == labour)
    assert after["estimate_line"] == before["estimate_line"]
    assert tasks_of(tree) == ["Câblage", "Essais", "Réception"]


@pytest.fixture
def scene(api: ContractClient, stage: Scene, costs: Costing) -> Rows:
    """Give the project In progress, its tasks and their lines, as the remaining tests have it."""

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **labour(costs, "Raccordement", "2", "10"))
        lines.made(wiring, **material(costs, "Fournitures", "1", "100"))
        tests = tree.made("Essais")
        lines.made(tests, **material(costs, "Banc", "1", "50"))
        lines.made(tests, **material(costs, "Câbles", "0", "20"))
        acceptance = tree.made("Réception")
        lines.made(acceptance, **material(costs, "Procès-verbal", "1", "10"))
        tree.made("Clôture")

    return Rows(stage, in_progress(api, stage, build), costs)


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_remaining_whose_structure_got_a_task_since_its_analysis_is_refused_nothing_written(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows, backups_bucket: Bucket
) -> None:
    # « Entre l'analyse et la confirmation, aucune donnée du projet n'a changé. » : a remaining to
    # commit analysed, a task created since; the connection at three days is not written.
    rows = scene.exported()
    rows[0][3] = 3
    import_id = remaining_analysed(
        api, stage, worker, remaining_workbook({OUTSIDE: rows}, scene.tasks())
    )
    connection = next(
        item
        for item in scene.tree.items()
        if item["kind"] == "estimate_line" and item["estimate_line"]["label"] == "Raccordement"
    )
    scene.tree.made("Mise en service")
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))
    kept = row_of(stage, connection["node_id"])
    assert (kept.hours, kept.reestimated_at) == (Decimal(10), None)


@pytest.mark.requirement("WF-ARC-0100-A")
def test_the_structure_written_is_named_before_a_terminal_project(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # The order of the 409 of ``applyImport``: ``import_structure_unchanged`` after
    # ``import_file_accepted`` and before the state of the project, ``project_not_terminal``.
    tree = planned(api, stage, worker)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    tree.made("Câblage du collègue")
    put_in_state(stage.owner, stage.project["project_id"], "abandoned")
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))


# --- Judged again when the task runs, under the lock of the structure -----------------------------


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_write_between_the_request_and_the_task_fails_the_task_and_refuses_the_import(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # « La condition est rejugée à l'exécution, sous le verrou de la structure : une écriture
    # arrivée entre la demande et la tâche fait échouer la tâche sur le même motif, l'import
    # refused. » The application suspends the writes of the service: the write is made around it,
    # a task inserted and the counter advanced, as a write in flight at the request would.
    tree = planned(api, stage, worker)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    key = stored(stage.database, import_id).object_key
    assert apply(api, stage, import_id).status_code == 202
    project, revision = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    structure = UUID(tree.structure_id)
    with stage.owner.begin() as connection:
        insert_task(connection, project, revision, structure, rank=3, label="En vol")
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == structure)
            .values(lock_version=CostStructure.lock_version + 1)
        )
    run(worker)
    assert task_problem(stage.database, import_id) == (STATE, CHANGED[2])
    assert read(api, stage, import_id)["status"] == "refused"
    assert backups_bucket.size(key) is None
    assert tasks_of(tree) == ["En vol", "T1", "T2"]


# --- A project without a current revision --------------------------------------------------------


def marked_planning(api: ContractClient, stage: Scene, worker: Worker) -> None:
    """Import the planning of two tasks into a revision, then mark it: no revision is current."""
    tree = planned(api, stage, worker)
    mark(stage, tree.revision)


@pytest.mark.story("US-3210")
def test_an_import_analysed_without_a_current_revision_applies_to_the_revision_it_creates(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # Propre à l'US : « un import analysé sur un projet sans révision en cours s'applique à la
    # révision qu'il crée ». The revision the task opens itself is not compared.
    marked_planning(api, stage, worker)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    applied_now(api, stage, worker, import_id)
    revision = read(api, stage, import_id)["revision_id"]
    assert tasks_of(Tree(api, stage, {"revision_id": revision})) == ["T1", "T2", "T3"]


@pytest.mark.story("US-3210")
def test_a_revision_opened_since_the_analysis_lets_the_import_apply_until_it_is_written(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # Propre à l'US : « si une révision a été ouverte puis écrite entre-temps, il est refusé de
    # même ». Two imports analysed on the marked revision; a revision opened since, its copy not
    # written: the first applies to it; the second then finds the copy written by the first.
    marked_planning(api, stage, worker)
    first = analysed(api, stage, worker, REWORKED)["import_id"]
    second = analysed(api, stage, worker, REWORKED)["import_id"]
    tree = Tree(api, stage, opened(api, stage))
    applied_now(api, stage, worker, first)
    assert tasks_of(tree) == ["T1", "T2", "T3"]
    refused_for_good(api, stage, backups_bucket, second, apply(api, stage, second))


@pytest.mark.story("US-3210")
def test_a_revision_opened_and_written_since_the_analysis_refuses_the_import(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # Propre à l'US : the copy of the structure read, written since its opening.
    marked_planning(api, stage, worker)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    tree = Tree(api, stage, opened(api, stage))
    tree.made("Câblage du collègue")
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))
    assert tasks_of(tree) == ["Câblage du collègue", "T1", "T2"]


@pytest.mark.story("US-3210")
def test_a_first_revision_opened_since_the_analysis_is_compared_as_its_opening_left_it(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # Propre à l'US : a project without any revision; two imports analysed without a structure,
    # the first revision opened since. The first import applies to it, unwritten; the second finds
    # its main structure written by the first.
    first = analysed(api, stage, worker, FIRST)["import_id"]
    second = analysed(api, stage, worker, REWORKED)["import_id"]
    assert stored(stage.database, first).structure_lock_version is None
    tree = Tree(api, stage, opened(api, stage))
    applied_now(api, stage, worker, first)
    assert tasks_of(tree) == ["T1", "T2"]
    refused_for_good(api, stage, backups_bucket, second, apply(api, stage, second))


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_copy_whose_opening_advanced_the_counter_further_refuses_the_import_though_unwritten(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    costs: Costing,
    backups_bucket: Bucket,
) -> None:
    # Fixes a behavior that is a limit, not a wish (#4791, a decision for the author):
    # ``unwritten_since_opening`` expects the opening to leave the counter of the copy at its first
    # value, or one more after the redating. An opening in a later reference year prices the lines
    # again and advances it further; the copy, written by no one, is judged written and the import
    # refused. The rule is not changed here: this test says what it does today.
    tree = planned(api, stage, worker)
    first = next(item for item in tree.items() if item["kind"] == "task")
    Lines(tree).made(first, quantity="1", resource_role_id=str(costs.role), hours="10")
    mark(stage, tree.revision)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    with pytest.MonkeyPatch.context() as clock:
        clock.setattr(
            "waterfall.api.revisions.utc_now", lambda: datetime(YEAR + 1, 1, 12, 10, tzinfo=UTC)
        )
        copy = Tree(api, stage, opened(api, stage))
    # The redated copy of a source that holds a node stands at 2: the opening went beyond.
    assert counter(stage, copy.structure_id) > 2
    refused_for_good(api, stage, backups_bucket, import_id, apply(api, stage, import_id))
    assert tasks_of(copy) == ["T1", "T2"]


# --- The rule of the durations, the counter null, the actual costs --------------------------------


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_new_analysis_of_a_change_of_rule_keeps_the_counter_it_reads(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « changer d'option rend un nouveau compte rendu, et le projet reste inchangé jusqu'à la
    # confirmation » : the new analysis keeps the counter it reads, and the application compares
    # that one — a task created before the change does not refuse it.
    eight, none = Decimal(8), Decimal(0)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CalendarRow)
            .where(CalendarRow.is_default)
            .values(
                monday=eight,
                tuesday=eight,
                wednesday=eight,
                thursday=eight,
                friday=eight,
                saturday=none,
                sunday=none,
            )
        )
    tree = Tree(api, stage, opened(api, stage))
    import_id = analysed(api, stage, worker, corpus(SYNTHETIC))["import_id"]
    first = stored(stage.database, import_id).structure_lock_version
    tree.made("Câblage du collègue")
    written = counter(stage, tree.structure_id)
    assert first is not None
    assert written > first
    answer = ruled(api, stage, import_id, "keep_dates")
    assert answer.status_code == 202, answer.text
    assert stored(stage.database, import_id).structure_lock_version is None
    run(worker)
    assert stored(stage.database, import_id).structure_lock_version == written
    applied_now(api, stage, worker, import_id)


@pytest.mark.story("US-3210")
def test_a_report_without_a_counter_applies_without_comparison(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # Propre à l'US (conception, « Décisions prises ») : a report analysed before the column, or by
    # a worker of before during an update, applies without comparison while it lives.
    tree = planned(api, stage, worker)
    import_id = analysed(api, stage, worker, REWORKED)["import_id"]
    with stage.owner.begin() as connection:
        connection.execute(
            update(ImportReport)
            .where(ImportReport.id == UUID(import_id))
            .values(structure_lock_version=None)
        )
    tree.made("Câblage du collègue")
    applied_now(api, stage, worker, import_id)
    assert "T3" in tasks_of(tree)


@pytest.mark.story("US-3210")
def test_an_extraction_of_actual_costs_keeps_no_counter_and_applies(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # Propre à l'US : the rule does not hold for the actual costs, which write in no structure.
    costs_in_progress(stage)
    declare(stage.database)
    subproject(api, stage)
    import_id = costs_analysed(api, stage, worker, extraction([line()]))["import_id"]
    assert stored(stage.database, import_id).structure_lock_version is None
    applied_now(api, stage, worker, import_id)
