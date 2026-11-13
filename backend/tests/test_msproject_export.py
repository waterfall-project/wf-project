# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The export of a planning of MS Project, and its round trip through the import (US-1430/L4).

Against the service, with a worker of the imports and the exports: a planning is imported into the
current revision, ``requestExport`` asks for its file, the worker writes it,
``getBackgroundTaskResult`` serves it, and the file is read by the reader of MSPDI or imported
again. Every answer is checked against the contract, the download of the file excepted (see
``download``). The writer itself, without a database, is tested in ``test_msproject``.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import deposited, path, read, run
from lxml import etree
from nodes_support import Tree, mark, opened
from planning_support import give_a_task, insert_link
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_import import Timing, link, links, planning, seven_hours_a_day, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.planning import exporting, importing
from waterfall.core.planning.msproject import read_project
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import read_tree
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.tables import DurationUnit
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.marking import mark as marking
from waterfall.worker.runner import Timing as WorkerTiming
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from datetime import date

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.core.planning.msproject import MsProject
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

KIND = "ms_project_schedule"
TASKS = "/api/v1/tasks"
AT_ONCE = WorkerTiming(claim_after=0, block=0.01, redeposit_every=0)
TUESDAY = "2026-11-03"
WEDNESDAY = "2026-11-04"
NOTES = "<Notes>Relever les armoires.\r\nPuis noter les écarts.</Notes>"
PERCENT = 19


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
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker that runs the imports and the exports, into the bucket of the test."""
    queue.prepare()
    imports = ImportTasks(backups_bucket)
    handlers = {
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "revision_mark": marking,
        "export": ExportTask(backups_bucket),
    }
    return Worker(database, queue, handlers, "worker", AT_ONCE)


def tuesday(duration: str = "PT8H0M0S", unit: str = "7") -> Timing:
    """Give the timing of a task of a day, from the Tuesday."""
    return Timing(f"{TUESDAY}T08:00:00", f"{TUESDAY}T17:00:00", duration, unit)


def the_planning() -> bytes:
    """Write a planning of a summary, a milestone, a manual task and the four types of link.

    A summary with two tasks (the first with notes) and a milestone, then a task of two elapsed
    days, one in hours, a manual one, and the percent of a lag; finish to start, start to start,
    finish to finish and start to finish, each with a lag in a unit of its own.
    """
    wednesday = Timing(f"{WEDNESDAY}T08:00:00", f"{WEDNESDAY}T17:00:00")
    return planning(
        task(1, "Études"),
        task(2, "Relevés", level=2, besides=NOTES),
        task(3, "Plans", level=2, besides=link(2), timing=tuesday()),
        task(4, "Revue", level=2, besides=link(3), timing=Timing(duration="PT0H0M0S")),
        task(5, "Pose", besides=link(4, 1, 4800, 7), timing=wednesday),
        task(6, "Câblage", besides=link(5, 3, 600, 5), timing=tuesday("PT48H0M0S", "8")),
        task(7, "Essais", besides=link(6, 0, 0, 7), timing=tuesday("PT2H0M0S", "5")),
        task(
            8,
            "Recette",
            besides="<Manual>1</Manual>" + link(7, 2, 50, PERCENT),
            timing=wednesday,
        ),
    )


def nodes(stage: Scene) -> list[tuple[Node, Task]]:
    """Read the tasks of the main structure of the current revision, in the order of the plan."""
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        structure_id = session.scalars(
            select(CostStructure.id)
            .where(CostStructure.project_id == project_id, CostStructure.kind == "main")
            .order_by(CostStructure.created_at.desc())
        ).first()
        assert structure_id is not None
        tree = read_tree(session, project_id, structure_id)
        session.expunge_all()
    return [(tree.nodes[each], tree.tasks[each]) for each in tree.order if each in tree.tasks]


def planning_start(stage: Scene) -> date | None:
    """Read the start of planning of the main structure of the current revision."""
    with stage.database.transaction() as session:
        return session.scalars(
            select(CostStructure.planning_start_on)
            .where(
                CostStructure.project_id == UUID(stage.project["project_id"]),
                CostStructure.kind == "main",
            )
            .order_by(CostStructure.created_at.desc())
        ).first()


def import_file(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, *, apply: bool
) -> dict[str, Any]:
    """Open the import of a file, analyse it and, if asked, apply it; give the import analysed."""
    upload_id = deposited(api, stage.manager, content)
    opening = api.post(
        path(stage), headers=stage.manager.headers, json={"kind": KIND, "upload_id": upload_id}
    )
    assert opening.status_code == 202, opening.text
    run(worker)
    found = read(api, stage, opening.json()["import_id"])
    assert found["status"] == "analysed", found
    if apply:
        confirmed = api.post(
            f"{path(stage, found['import_id'])}/apply",
            headers=stage.manager.headers,
            json={"confirmed": True},
        )
        assert confirmed.status_code == 202, confirmed.text
        run(worker)
        assert read(api, stage, found["import_id"])["status"] == "applied"
    return found


def request_export(api: ContractClient, stage: Scene, revision_id: str, **body: Any) -> Any:
    """Ask for the export of a revision as the manager does; give the answer."""
    return api.post(
        f"{PROJECTS}/{stage.project['project_id']}/exports",
        headers=stage.manager.headers,
        json={"kind": KIND, "revision_id": revision_id, **body},
    )


def download(api: ContractClient, stage: Scene, task_id: str) -> Any:
    """Download the result of an export as the manager does; give the answer."""
    return api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)


def exported_answer(api: ContractClient, stage: Scene, worker: Worker, revision_id: str) -> Any:
    """Export the planning of a revision and download its file; give the answer."""
    asked = request_export(api, stage, revision_id)
    assert asked.status_code == 202, asked.text
    assert worker.step()
    answer = download(api, stage, asked.json()["task_id"])
    assert answer.status_code == 200, answer.text
    assert answer.headers["content-type"].startswith("application/xml")
    return answer


def exported(api: ContractClient, stage: Scene, worker: Worker, revision_id: str) -> bytes:
    """Export the planning of a revision and download its file; give its content."""
    return bytes(exported_answer(api, stage, worker, revision_id).content)


def exported_planning(api: ContractClient, stage: Scene, worker: Worker) -> tuple[bytes, MsProject]:
    """Import the planning above into a new revision, export it; give the file and what it says."""
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    content = exported(api, stage, worker, revision["revision_id"])
    return content, read_project(content).project


@pytest.mark.requirement("WF-INTF-0060-A")
def test_a_planning_exported_then_imported_again_presents_no_difference_no_date_mismatch(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Le compte rendu ne présente aucun écart de dates ni de durées, et le planning obtenu est
    # identique à celui relevé avant l'export. » A summary, a milestone, the four types of link.
    content, _ = exported_planning(api, stage, worker)
    before = [
        (node.id, node.lineage_id, node.parent_id, task.start_date, task.start_hours)
        for node, task in nodes(stage)
    ]
    found = import_file(api, stage, worker, content, apply=False)
    report = found["report"]
    assert (report["differences"], report["date_mismatches"]) == ([], [])
    assert (report["refusals"], report["rejected"], report["signals"]) == ([], [], [])
    assert report["unchanged_count"] == report["read_count"] == 8
    again = import_file(api, stage, worker, content, apply=True)
    assert again["report"]["differences"] == []
    after = [
        (node.id, node.lineage_id, node.parent_id, task.start_date, task.start_hours)
        for node, task in nodes(stage)
    ]
    assert after == before


@pytest.mark.requirement("WF-INTF-0060-A")
def test_the_start_of_planning_and_the_description_of_each_task_are_the_same_after_the_round_trip(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « La date de début de planning est identique avant et après l'aller-retour. » « La
    # description de chaque tâche est identique avant et après l'aller-retour. » (#1339)
    content, project = exported_planning(api, stage, worker)
    start = planning_start(stage)
    descriptions = [task.description for _, task in nodes(stage)]
    assert descriptions[1] == "Relever les armoires.\nPuis noter les écarts."
    assert descriptions.count(None) == 7
    assert project.start is not None
    assert project.start.date() == start
    import_file(api, stage, worker, content, apply=True)
    assert planning_start(stage) == start
    assert [task.description for _, task in nodes(stage)] == descriptions


@pytest.mark.requirement("WF-INTF-0050-A")
def test_each_task_carries_its_lineage_its_notes_its_calendar_and_the_default_calendar_is_listed(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Les calendriers Waterfall y figurent et sont affectés aux tâches, et chaque tâche porte
    # son identifiant Waterfall et, dans ses notes, sa description. »
    _, project = exported_planning(api, stage, worker)
    kept = nodes(stage)
    assert [each.name for each in project.tasks] == [task.label for _, task in kept]
    assert [each.lineage for each in project.tasks] == [node.lineage_id for node, _ in kept]
    assert [each.notes for each in project.tasks] == [task.description for _, task in kept]
    assert [each.uid for each in project.tasks] == list(range(1, 9))
    assert [each.outline_level for each in project.tasks] == [1, 2, 2, 2, 1, 1, 1, 1]
    # The default calendar is the calendar of the project, listed by the seven days of its week.
    assert [each.uid for each in project.calendars] == [project.calendar_uid] == [1]
    calendar = project.calendars[0]
    assert (calendar.is_base, len(calendar.days)) == (True, 7)
    assert {day.day_type: day.working for day in calendar.days} == {
        1: False,
        2: True,
        3: True,
        4: True,
        5: True,
        6: True,
        7: False,
    }
    assert {each.calendar_uid for each in project.tasks} == {1}


@pytest.mark.requirement("WF-PLA-0160-A")
def test_the_constants_and_the_durations_are_exported_in_their_unit_and_the_installation_hours(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Exportés sans perte : modes, durées dans leur unité, constantes. »
    _, project = exported_planning(api, stage, worker)
    assert (project.minutes_per_day, project.minutes_per_week, project.days_per_month) == (
        480,
        2400,
        20,
    )
    found = {each.name: each for each in project.tasks}
    assert {name: each.duration_unit for name, each in found.items()} == {
        "Études": "d",
        "Relevés": "d",
        "Plans": "d",
        "Revue": "d",
        "Pose": "d",
        "Câblage": "ed",
        "Essais": "h",
        "Recette": "d",
    }
    assert found["Câblage"].duration is not None
    assert found["Câblage"].duration.total_seconds() == 2 * 24 * 3600
    assert found["Essais"].duration is not None
    assert found["Essais"].duration.total_seconds() == 2 * 3600
    assert found["Pose"].duration is not None
    assert found["Pose"].duration.total_seconds() == 8 * 3600
    assert (found["Revue"].milestone, found["Revue"].duration_unit) == (True, "d")
    assert not found["Plans"].milestone
    assert found["Études"].duration_unit == "d"


@pytest.mark.requirement("WF-PLA-0030-A")
def test_the_modes_the_types_and_the_lags_of_the_links_are_exported_without_loss(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Exportés sans perte : modes, […] liaisons : type et décalage dans son unité. »
    _, project = exported_planning(api, stage, worker)
    found = {each.name: each for each in project.tasks}
    assert [each.name for each in project.tasks if each.manual] == ["Recette"]
    uids = {name: each.uid for name, each in found.items()}
    wanted = {
        "Plans": [(uids["Relevés"], "finish_to_start", 0, "d")],
        "Pose": [(uids["Revue"], "finish_to_start", 4800, "d")],
        "Câblage": [(uids["Pose"], "start_to_start", 600, "h")],
        "Essais": [(uids["Câblage"], "finish_to_finish", 0, "d")],
        "Recette": [(uids["Essais"], "start_to_finish", 50, "percent")],
        "Études": [],
    }
    for name, expected in wanted.items():
        links = [
            (each.predecessor_uid, each.link_type, each.lag, each.lag_unit)
            for each in found[name].predecessors
        ]
        assert links == expected, name


@pytest.mark.requirement("WF-INTF-0050-A")
def test_an_export_is_requested_for_a_marked_revision_and_served_once_under_its_name(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « requestExport dépose une tâche export (202) pour la révision nommée, en cours ou
    # marquée, la structure principale par défaut, sous export_planning […] ;
    # getBackgroundTaskResult répond 409 task_succeeded avant, 404 après. »
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    revision_id = revision["revision_id"]
    mark(stage, revision)
    asked = request_export(api, stage, revision_id)
    assert asked.status_code == 202, asked.text
    body = asked.json()
    assert (body["kind"], body["status"], body["result_url"]) == ("export", "queued", None)
    task_id = body["task_id"]
    before = api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)
    assert before.status_code == 409
    assert before.json()["params"] == {"missing_condition": "task_succeeded"}
    assert worker.step()
    done = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers)
    assert done.status_code == 200, done.text
    assert (done.json()["status"], done.json()["result_url"]) == (
        "succeeded",
        f"{TASKS}/{task_id}/result",
    )
    served = download(api, stage, task_id)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("application/xml")
    disposition = served.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="ms-project')
    assert disposition.endswith('.xml"')
    assert [each.name for each in read_project(served.content).project.tasks][:2] == [
        "Études",
        "Relevés",
    ]
    after = api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)
    assert after.status_code == 404
    assert api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers).json()["result_url"] is None


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_file_exported_is_valid_against_the_schema_when_it_is_named(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Le fichier est valide contre le schéma quand il est présent » (WF-QUA-0080: the schema is
    # a setting, the test skipped without it).
    named = os.environ.get("WATERFALL_MSPDI_SCHEMA_PATH")
    if not named:
        pytest.skip("WATERFALL_MSPDI_SCHEMA_PATH names no schema of MSPDI")
    content, _ = exported_planning(api, stage, worker)
    schema = etree.XMLSchema(etree.parse(Path(named)))
    schema.assertValid(etree.fromstring(content))


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_file_exported_says_to_ms_project_its_working_day_and_the_dates_of_a_manual_task(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un planning Waterfall exporté […] s'ouvre sans erreur » et « MS Project recalcule pour
    # chaque tâche des dates de début et de fin identiques » (#2923), read in the XML exported and
    # not as the reader of Waterfall reads it back: on days of seven hours, the head says 8:00 to
    # 15:00, no duration is estimated, and a manual task and a manual milestone carry their dates
    # and their duration again in the fields ``Manual…``, the milestone a nought duration.
    seven_hours_a_day(stage)
    revision = opened(api, stage)
    import_file(
        api,
        stage,
        worker,
        planning(
            task(1, "Relevés"),
            task(2, "Pose", besides="<Manual>1</Manual>", timing=tuesday("PT16H0M0S")),
            task(
                3,
                "Livrée",
                besides="<Manual>1</Manual>",
                timing=Timing(f"{WEDNESDAY}T17:00:00", f"{WEDNESDAY}T17:00:00", "PT0H0M0S"),
            ),
        ),
        apply=True,
    )
    root = etree.fromstring(exported(api, stage, worker, revision["revision_id"]))
    assert (root.findtext("{*}DefaultStartTime"), root.findtext("{*}DefaultFinishTime")) == (
        "08:00:00",
        "15:00:00",
    )
    written = {
        task.findtext("{*}Name"): {etree.QName(child).localname: child.text for child in task}
        for task in root.iterfind("{*}Tasks/{*}Task")
    }
    assert [fields["Estimated"] for fields in written.values()] == ["0", "0", "0"]
    assert not {"ManualStart", "ManualFinish", "ManualDuration"} & written["Relevés"].keys()
    for name in ("Pose", "Livrée"):
        fields = written[name]
        assert fields["Manual"] == "1"
        assert (fields["ManualStart"], fields["ManualFinish"], fields["ManualDuration"]) == (
            fields["Start"],
            fields["Finish"],
            fields["Duration"],
        ), name
    assert (written["Livrée"]["Milestone"], written["Livrée"]["ManualDuration"]) == (
        "1",
        "PT0H0M0S",
    )


@pytest.mark.requirement("WF-INTF-0050-A")
def test_a_task_on_a_calendar_of_other_hours_gets_a_calendar_of_its_own_after_the_project_one(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un calendrier de projet et un calendrier de tâche par calendrier applicable distinct » :
    # the calendar of a task is the one of the role of its line (EP-07, ``register_facet``).
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    pose = next(node.id for node, task in nodes(stage) if task.label == "Pose")
    costing(stage.database)
    workshop = add_role(stage.database, "ATEL", (10, 10, 10, 10, 0, 0, 0))
    Lines(Tree(api, stage, revision)).made(
        str(pose), quantity="1", resource_role_id=str(workshop), hours="8"
    )
    project = read_project(exported(api, stage, worker, revision["revision_id"])).project
    assert [(each.uid, each.name, each.is_base) for each in project.calendars] == [
        (1, "Waterfall", True),
        (2, "Waterfall 2", True),
    ]
    assert project.calendar_uid == 1
    assert {each.name: each.calendar_uid for each in project.tasks} == {
        "Études": 1,
        "Relevés": 1,
        "Plans": 1,
        "Revue": 1,
        "Pose": 2,
        "Câblage": 1,
        "Essais": 1,
        "Recette": 1,
    }
    worked = [day for day in project.calendars[1].days if day.working]
    assert [day.day_type for day in worked] == [2, 3, 4, 5]
    assert {day.times[0][1].hour - day.times[0][0].hour for day in worked} == {10}


def lagged_planning(month_lag: int = 96000, month: str = "PT160H0M0S") -> bytes:
    """Write a chain of six tasks, each linked to the one before by a lag of another unit.

    Finish to start with a lag of minus two days, of a week, of a month (``month_lag`` tenths of a
    minute) and of an elapsed day, then start to finish by a percent; the last lasts a month,
    which is ``month`` of hours.
    """
    return planning(
        task(1, "A"),
        task(2, "B", besides=link(1, 1, -9600, 7)),
        task(3, "C", besides=link(2, 1, 24000, 9)),
        task(4, "D", besides=link(3, 1, month_lag, 11)),
        task(5, "E", besides=link(4, 1, 14400, 8)),
        task(6, "F", timing=Timing(duration=month, unit="11"), besides=link(5, 2, 50, PERCENT)),
    )


def lags_of(project: MsProject) -> dict[str, list[tuple[int, str | None]]]:
    """Give the lag and the unit of each link of a project, by task."""
    return {
        each.name: [(one.lag, one.lag_unit) for one in each.predecessors] for each in project.tasks
    }


CHAIN = {
    ("A", "B", "finish_to_start", Decimal(-2), "d"),
    ("B", "C", "finish_to_start", Decimal(1), "w"),
    ("C", "D", "finish_to_start", Decimal(1), "mo"),
    ("D", "E", "finish_to_start", Decimal(1), "ed"),
    ("E", "F", "start_to_finish", Decimal(50), "percent"),
}


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_negative_lag_a_lag_in_weeks_in_months_and_an_elapsed_one_are_exported_without_loss(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un décalage négatif exporté sans perte. » « Exportés sans perte : […] liaisons : type et
    # décalage dans son unité. » The hours of a lag are the file's tenths of a minute, a percent its
    # whole percents.
    revision = opened(api, stage)
    import_file(api, stage, worker, lagged_planning(), apply=True)
    content = exported(api, stage, worker, revision["revision_id"])
    assert lags_of(read_project(content).project) == {
        "A": [],
        "B": [(-9600, "d")],
        "C": [(24000, "w")],
        "D": [(96000, "mo")],
        "E": [(14400, "ed")],
        "F": [(50, "percent")],
    }
    found = import_file(api, stage, worker, content, apply=False)
    assert found["report"]["differences"] == []


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_lag_of_a_fraction_of_a_percent_is_exported_rounded_half_up_and_comes_back_so(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # MS Project carries a lag in percent in whole percents (``LinkLag``): 12.5 % entered is
    # written 13 % — a half up, not to the even 12 — and comes back 13 %, the loss of the round
    # trip.
    revision = opened(api, stage)
    import_file(api, stage, worker, lagged_planning(), apply=True)
    with stage.owner.begin() as connection:
        connection.execute(
            update(TaskLink).where(TaskLink.lag_unit == "percent").values(lag_value=Decimal("12.5"))
        )
    content = exported(api, stage, worker, revision["revision_id"])
    assert lags_of(read_project(content).project)["F"] == [(13, "percent")]
    import_file(api, stage, worker, content, apply=True)
    assert ("E", "F", "start_to_finish", Decimal(13), "percent") in links(stage)


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_lag_entered_in_weeks_or_months_is_exported_then_imported_again_in_its_unit(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un décalage saisi 1 sem est exporté puis réimporté sans changer d'unité. »
    revision = opened(api, stage)
    import_file(api, stage, worker, lagged_planning(), apply=True)
    assert links(stage) == CHAIN
    content = exported(api, stage, worker, revision["revision_id"])
    import_file(api, stage, worker, content, apply=True)
    assert links(stage) == CHAIN


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_days_per_month_that_is_not_whole_is_written_whole_and_the_months_are_kept(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # The schema writes the constants as integers: 21.67 days a month is written 22. The durations
    # and the lags travel in hours, and the import takes no constant of the file, so the months
    # entered come back as they were, the report presenting no difference.
    with stage.owner.begin() as connection:
        connection.execute(update(DurationUnit).values(days_per_month=Decimal("21.67")))
    revision = opened(api, stage)
    # A month is 21.67 days of 8 hours: 173.36 hours, 173 h 21 min 36 s, 104016 tenths of a minute.
    import_file(api, stage, worker, lagged_planning(104016, "PT173H21M36S"), apply=True)
    before = (links(stage), [(each.duration_value, each.duration_unit) for _, each in nodes(stage)])
    assert ("C", "D", "finish_to_start", Decimal(1), "mo") in before[0]
    content = exported(api, stage, worker, revision["revision_id"])
    assert read_project(content).project.days_per_month == 22
    found = import_file(api, stage, worker, content, apply=False)
    assert found["report"]["differences"] == []
    import_file(api, stage, worker, content, apply=True)
    after = (links(stage), [(each.duration_value, each.duration_unit) for _, each in nodes(stage)])
    assert after == before


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_file_is_named_after_the_code_of_the_project_cleaned_or_not_at_all(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # A project without a code (the stage's) is served as ``ms-project.xml``, one with a code as
    # ``ms-project-<code>.xml``, each run of characters that are no name's turned into an
    # underscore, and a code of such characters alone is no code.
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    project_id = UUID(stage.project["project_id"])

    def named(code: str | None) -> str:
        with stage.owner.begin() as connection:
            connection.execute(update(Project).where(Project.id == project_id).values(code=code))
        answer = exported_answer(api, stage, worker, revision["revision_id"])
        return str(answer.headers["content-disposition"])

    assert named(None) == 'attachment; filename="ms-project.xml"'
    assert named("PRJ é-1") == 'attachment; filename="ms-project-PRJ_-1.xml"'
    assert named("é é") == 'attachment; filename="ms-project.xml"'


def test_the_currency_code_written_is_the_one_of_the_installation(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # CurrencyCode, that the schema requires, bears the currency of the installation, not an empty
    # value (#2469). It cites no requirement: the Vérif of WF-QUA-0080-A (the corpus imported then
    # exported, valid against the schema) is not what it tries, the corpus tries it whole; nor is
    # the opening in MS Project of WF-INTF-0050-A, checked at acceptance (#2682). A detail of the
    # code, as WF-QUA-0010 admits.
    with stage.database.transaction() as session:
        currency = read_reference_settings(session).currency_code
    content, project = exported_planning(api, stage, worker)
    assert currency
    assert project.currency_code == currency
    assert f"<CurrencyCode>{currency}</CurrencyCode>" in content.decode()


def test_a_link_created_while_the_planning_is_exported_is_not_read_and_the_export_succeeds(
    api: ContractClient, stage: Scene, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The export reads in a transaction frozen at its first read (#2679): a task and a link from
    # it, committed between the reading of the tree and that of the links, are not read — the link
    # would name a task the tree read has not —, and the planning is exported as it stood.
    revision = opened(api, stage)
    revision_id = UUID(revision["revision_id"])
    import_file(api, stage, worker, the_planning(), apply=True)
    successor = nodes(stage)[-1][0].id
    reading = exporting.read_links

    def meanwhile(session: Session, project_id: UUID, structure_id: UUID) -> list[TaskLink]:
        with stage.database.engine.begin() as connection:
            created = give_a_task(connection, revision_id)
            connection.execute(
                insert_link(project_id, revision_id, structure_id, created, successor)
            )
        return reading(session, project_id, structure_id)

    monkeypatch.setattr(exporting, "read_links", meanwhile)
    exported_project = read_project(exported(api, stage, worker, revision["revision_id"])).project
    monkeypatch.undo()
    assert len(exported_project.tasks) == len(read_project(the_planning()).project.tasks)
    again = read_project(exported(api, stage, worker, revision["revision_id"])).project
    assert len(again.tasks) == len(exported_project.tasks) + 1


def test_a_link_created_while_the_planning_is_analysed_is_not_read_and_the_analysis_succeeds(
    api: ContractClient, stage: Scene, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The analysis reads in a transaction frozen at its first read (#2679), as the export does: a
    # task and a link from it, committed between the reading of the tree and that of the links,
    # are not read — the link would name a task the tree read has not.
    revision = opened(api, stage)
    revision_id = UUID(revision["revision_id"])
    import_file(api, stage, worker, the_planning(), apply=True)
    successor = nodes(stage)[-1][0].id
    reading = importing.read_links

    def meanwhile(session: Session, project_id: UUID, structure_id: UUID) -> list[TaskLink]:
        with stage.database.engine.begin() as connection:
            created = give_a_task(connection, revision_id)
            connection.execute(
                insert_link(project_id, revision_id, structure_id, created, successor)
            )
        return reading(session, project_id, structure_id)

    monkeypatch.setattr(importing, "read_links", meanwhile)
    found = import_file(api, stage, worker, the_planning(), apply=False)
    assert found["status"] == "analysed"
