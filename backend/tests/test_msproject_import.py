# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a planning of MS Project: its analysis, its report, its application (US-1430/L3).

Against the service, with the worker of the imports: a file of the corpus (``fixtures/msproject``)
or a small planning written here, deposited, opened, analysed — its report read as the contract
reads it —, then applied, and the structure read back. The tests of the corpus itself, without a
database, are in ``test_msproject_corpus.py``.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from imports_trial import deposited, import_worker, path, read, refusal, run
from nodes_support import opened, put_facts, set_progress, work_breakdown
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.planning.interface.msproject import recognised
from waterfall.core.planning.msproject import (
    calendar_of,
    calendars_of,
    constants_of,
    read_project,
)
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tree import read_links, read_tree
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.core.planning.tables import Node, Task
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "msproject"
KIND = "ms_project_schedule"
# The Monday the small plannings of these tests start on, and their calendar: eight hours.
MONDAY = "2026-11-02"
FRIDAY = "2026-11-06T17:00:00"
STANDARD = (
    """<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>
<WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
<WeekDay><DayType>7</DayType><DayWorking>0</DayWorking></WeekDay>
"""
    + "".join(
        f"""<WeekDay><DayType>{day}</DayType><DayWorking>1</DayWorking><WorkingTimes>
<WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
<WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
</WorkingTimes></WeekDay>"""
        for day in range(2, 7)
    )
    + "</WeekDays></Calendar></Calendars>"
)


@dataclass(frozen=True, slots=True)
class Timing:
    """The dates of a task of a small planning, its duration and the format of its unit."""

    start: str = f"{MONDAY}T08:00:00"
    finish: str = f"{MONDAY}T17:00:00"
    duration: str = "PT8H0M0S"
    unit: str = "7"


A_DAY = Timing()


def task(uid: int, name: str, *, level: int = 1, besides: str = "", timing: Timing = A_DAY) -> str:
    """Write a task of a small planning: a day from the Monday, automatic, unless said."""
    start, finish, duration, unit = timing.start, timing.finish, timing.duration, timing.unit
    return (
        f"<Task><UID>{uid}</UID><Name>{name}</Name><OutlineLevel>{level}</OutlineLevel>"
        f"<Start>{start}</Start><Finish>{finish}</Finish><Duration>{duration}</Duration>"
        f"<DurationFormat>{unit}</DurationFormat>{besides}</Task>"
    )


def link(predecessor: int, kind: int = 1, lag: int = 0, unit: int = 7) -> str:
    """Write a link to a predecessor: finish to start without lag, unless said."""
    return (
        f"<PredecessorLink><PredecessorUID>{predecessor}</PredecessorUID><Type>{kind}</Type>"
        f"<LinkLag>{lag}</LinkLag><LagFormat>{unit}</LagFormat></PredecessorLink>"
    )


def planning(*tasks: str, minutes: tuple[int, int] = (480, 2400), besides: str = "") -> bytes:
    """Write a small planning of MS Project, saved as MS Project saves it, on the calendar above."""
    per_day, per_week = minutes
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Project xmlns="http://schemas.microsoft.com/project">'
        f"<StartDate>{MONDAY}T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
        f"<MinutesPerDay>{per_day}</MinutesPerDay><MinutesPerWeek>{per_week}</MinutesPerWeek>"
        f"<DaysPerMonth>20</DaysPerMonth>{besides}{STANDARD}<Tasks>{''.join(tasks)}</Tasks>"
        "</Project>"
    ).encode()


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
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def opening(api: ContractClient, stage: Scene, content: bytes) -> Any:
    """Deposit a planning and open its import as the manager does; give the answer."""
    upload_id = deposited(api, stage.manager, content)
    return api.post(
        path(stage), headers=stage.manager.headers, json={"kind": KIND, "upload_id": upload_id}
    )


def analysed(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> dict[str, Any]:
    """Open the import of a planning and run its analysis; give the import analysed."""
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, response.json()["import_id"])
    assert found["status"] == "analysed", found
    return found


def applied(api: ContractClient, stage: Scene, worker: Worker, found: dict[str, Any]) -> None:
    """Confirm the application of an import analysed, and run it to its end."""
    response = api.post(
        f"{path(stage, found['import_id'])}/apply",
        headers=stage.manager.headers,
        json={"confirmed": True},
    )
    assert response.status_code == 202, response.text
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "applied"


def imported(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> dict[str, Any]:
    """Import a planning, analysed then applied; give its report."""
    found = analysed(api, stage, worker, content)
    applied(api, stage, worker, found)
    return found["report"]


def main_structure(stage: Scene) -> UUID:
    """Give the main structure of the current revision of the project of the stage."""
    with stage.database.transaction() as session:
        return session.scalars(
            select(CostStructure.id)
            .where(
                CostStructure.project_id == UUID(stage.project["project_id"]),
                CostStructure.kind == "main",
            )
            .order_by(CostStructure.created_at.desc())
        ).first() or UUID(int=0)


def tasks(stage: Scene) -> list[tuple[Node, Task]]:
    """Read the tasks of the main structure, in the order of the plan."""
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        tree = read_tree(session, project_id, main_structure(stage))
        session.expunge_all()
    return [(tree.nodes[each], tree.tasks[each]) for each in tree.order if each in tree.tasks]


def by_label(stage: Scene) -> dict[str, tuple[Node, Task]]:
    """Read the tasks of the main structure by their label."""
    return {task.label: (node, task) for node, task in tasks(stage)}


def links(stage: Scene) -> set[tuple[str, str, str, Decimal, str]]:
    """Read the links of the main structure, each by its two labels, its type and its lag."""
    project_id = UUID(stage.project["project_id"])
    labels = {node.id: task.label for node, task in tasks(stage)}
    with stage.database.transaction() as session:
        found = read_links(session, project_id, main_structure(stage))
        return {
            (
                labels[each.predecessor_id],
                labels[each.successor_id],
                each.link_type,
                each.lag_value.normalize(),
                each.lag_unit,
            )
            for each in found
        }


def seven_hours_a_day(stage: Scene) -> None:
    """Give the default calendar the days of the corpus: seven hours, Monday to Friday."""
    hours = Decimal(7)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Calendar)
            .where(Calendar.is_default)
            .values(monday=hours, tuesday=hours, wednesday=hours, thursday=hours, friday=hours)
        )


def corpus(file: str) -> bytes:
    """Read a planning of the corpus."""
    return (CORPUS / file).read_bytes()


def instant(day: str, hours: str) -> WorkInstant:
    """Give an instant of work."""
    return WorkInstant(date.fromisoformat(day), Decimal(hours))


def dates(task: Task) -> tuple[WorkInstant, WorkInstant]:
    """Give the dates of a task as they are kept."""
    return (
        WorkInstant(task.start_date, task.start_hours.normalize()),
        WorkInstant(task.finish_date, task.finish_hours.normalize()),
    )


@pytest.mark.requirement("WF-INTF-0040-A")
@pytest.mark.requirement("WF-PLA-0030-A")
@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_file_saved_by_ms_project_is_imported_with_its_tasks_links_and_dates(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un fichier XML produit par MS Project 2013 est importé sans erreur. Après import, les
    # tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et décalage — sont
    # identiques à celles du fichier source. » The project has no revision yet: the application
    # creates it, the date of the project its planning start.
    seven_hours_a_day(stage)
    content = corpus("01-links-and-lags-days.xml")
    report = imported(api, stage, worker, content)
    added = [each["label"] for each in report["differences"] if each["target"] == "task"]
    project = read_project(content).project
    assert added == [each.name for each in project.tasks]
    assert (report["read_count"], report["unchanged_count"]) == (8, 0)
    assert (report["rejected"], report["refusals"], report["date_mismatches"]) == ([], [], [])
    assert report["ignored"] == [{"kind": "calendars", "count": 1, "labels": ["Standard"]}]
    kept = tasks(stage)
    assert [task.label for _, task in kept] == added
    assert [task.external_id for _, task in kept] == [str(each.uid) for each in project.tasks]
    calendars = calendars_of(project)
    for (_, task), each in zip(kept, project.tasks, strict=True):
        calendar = calendar_of(project, calendars, each)
        assert calendar is not None
        assert each.start is not None
        assert each.finish is not None
        assert dates(task) == (calendar.instant(each.start), calendar.instant(each.finish))
    first, second, third, fourth, fifth, sixth, seventh, eighth = added
    assert links(stage) == {
        (first, second, "finish_to_start", Decimal(0), "d"),
        (second, third, "finish_to_start", Decimal(2), "d"),
        (third, fourth, "start_to_start", Decimal(-1), "d"),
        (fourth, fifth, "finish_to_finish", Decimal(0), "d"),
        (fifth, sixth, "finish_to_finish", Decimal(3), "d"),
        (second, seventh, "start_to_finish", Decimal(0), "d"),
        (sixth, eighth, "finish_to_start", Decimal(0), "d"),
    }
    with stage.database.transaction() as session:
        start = session.scalar(
            select(CostStructure.planning_start_on).where(CostStructure.id == main_structure(stage))
        )
    assert start == date(2009, 11, 16)


@pytest.mark.requirement("WF-INTF-0060-A")
def test_a_planning_reimported_unchanged_presents_no_difference_and_keeps_its_start(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Le compte rendu ne présente aucun écart de dates ni de durées, et le planning obtenu est
    # identique à celui relevé avant […]. La date de début de planning est identique avant et
    # après. » Summaries on four levels, milestones, links to and from summaries, a manual one.
    seven_hours_a_day(stage)
    opened(api, stage)
    content = corpus("05-summaries-and-milestones.xml")
    first = imported(api, stage, worker, content)
    assert (first["date_mismatches"], first["signals"], first["refusals"]) == ([], [], [])
    assert first["differences"][0]["fields"] == ["planning_start_on"]
    before = [
        (node.id, node.lineage_id, node.parent_id, dates(task)) for node, task in tasks(stage)
    ]
    again = analysed(api, stage, worker, content)["report"]
    assert (again["differences"], again["date_mismatches"], again["signals"]) == ([], [], [])
    assert again["unchanged_count"] == again["read_count"] == 23
    applied(api, stage, worker, analysed(api, stage, worker, content))
    after = [(node.id, node.lineage_id, node.parent_id, dates(task)) for node, task in tasks(stage)]
    assert after == before
    manual = by_label(stage)["T0"][1]
    assert (manual.scheduling_mode, dates(manual)) == (
        "manual",
        (instant("2009-11-16", "0"), instant("2009-11-16", "0")),
    )


@pytest.mark.requirement("WF-INTF-0040-A")
@pytest.mark.requirement("WF-INTF-0060-A")
def test_the_description_of_a_task_is_read_in_its_notes_and_unchanged_by_a_reimport(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « La description de chaque tâche est identique avant et après l'aller-retour. » (#1339)
    opened(api, stage)
    notes = "<Notes>Câbler les armoires.\r\nPuis les essayer.</Notes>"
    content = planning(task(1, "Câblage", besides=notes), task(2, "Essais"))
    imported(api, stage, worker, content)
    found = by_label(stage)
    assert found["Câblage"][1].description == "Câbler les armoires.\nPuis les essayer."
    assert found["Essais"][1].description is None
    assert analysed(api, stage, worker, content)["report"]["differences"] == []


@pytest.mark.requirement("WF-PLA-0020-A")
@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_manual_task_keeps_its_dates_and_one_on_a_saturday_is_kept_and_signalled(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « La même date importée d'un fichier MS Project est gardée et signalée au compte rendu. »
    # « Une tâche en mode manuel du fichier est en mode manuel aux mêmes dates. »
    opened(api, stage)
    manual = "<Manual>1</Manual>"
    saturday = Timing("2026-11-07T08:00:00", "2026-11-07T17:00:00")
    tuesday = Timing("2026-11-03T10:00:00", "2026-11-03T14:00:00", "PT3H0M0S", "5")
    content = planning(
        task(1, "Livraison", besides=manual, timing=saturday),
        task(2, "Revue", besides=manual, timing=tuesday),
    )
    report = imported(api, stage, worker, content)
    params = {"date": "2026-11-07", "next_working_day": "2026-11-09"}
    assert report["signals"] == [
        {
            "lineage_id": None,
            "label": "Livraison",
            "column": column,
            "code": "NON_WORKING_DAY",
            "params": params,
        }
        for column in ("start", "finish")
    ]
    found = by_label(stage)
    delivery, review = found["Livraison"][1], found["Revue"][1]
    assert (delivery.scheduling_mode, dates(delivery)) == (
        "manual",
        (instant("2026-11-07", "0"), instant("2026-11-07", "0")),
    )
    assert (review.scheduling_mode, dates(review)) == (
        "manual",
        (instant("2026-11-03", "2"), instant("2026-11-03", "5")),
    )


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_summary_in_manual_mode_is_imported_automatic_and_signalled_with_its_dates(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une récapitulative en mode manuel dans le fichier est importée en mode automatique, et le
    # compte rendu la signale avec l'écart de dates. »
    opened(api, stage)
    content = planning(
        task(1, "Études", besides="<Manual>1</Manual>", timing=Timing(finish=FRIDAY)),
        task(2, "Conception", level=2),
    )
    report = imported(api, stage, worker, content)
    assert report["signals"] == [
        {
            "lineage_id": None,
            "label": "Études",
            "column": "scheduling_mode",
            "code": "SUMMARY_TASK_DERIVED",
            "params": {"start": MONDAY, "finish": "2026-11-06"},
        }
    ]
    assert report["date_mismatches"] == [
        {"lineage_id": None, "label": "Études", "fields": ["finish"]}
    ]
    assert by_label(stage)["Études"][1].scheduling_mode == "automatic"


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_constrained_task_is_manual_a_started_one_not_started_and_both_said_ignored(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; une
    # tâche à 50 % d'avancement est importée non démarrée. »
    opened(api, stage)
    constrained = (
        "<ConstraintType>4</ConstraintType><ConstraintDate>2026-11-03T08:00:00</ConstraintDate>"
    )
    later = Timing("2026-11-03T08:00:00", "2026-11-03T17:00:00")
    content = planning(
        task(1, "Réception", besides=constrained, timing=later),
        task(2, "Montage", besides="<PercentComplete>50</PercentComplete>"),
    )
    report = imported(api, stage, worker, content)
    assert report["ignored"] == [
        {"kind": "calendars", "count": 1, "labels": ["Standard"]},
        {"kind": "progress", "count": 1, "labels": []},
        {"kind": "date_constraints", "count": 1, "labels": ["Réception"]},
    ]
    found = by_label(stage)
    reception, assembly = found["Réception"][1], found["Montage"][1]
    assert (reception.scheduling_mode, dates(reception)) == (
        "manual",
        (instant("2026-11-03", "0"), instant("2026-11-03", "8")),
    )
    assert (assembly.progress, assembly.started_on) == ("not_started", None)


@pytest.mark.requirement("WF-INTF-0040-A")
def test_the_resources_and_calendars_of_a_file_are_neither_created_nor_silent(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans
    # Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. »
    opened(api, stage)

    def counted() -> tuple[int, int]:
        with stage.database.transaction() as session:
            calendars = session.scalar(select(func.count()).select_from(Calendar))
            roles = session.scalar(select(func.count()).select_from(ResourceRole))
            return calendars or 0, roles or 0

    before = counted()
    report = imported(api, stage, worker, corpus("13-resource-calendars-not-ignored.xml"))
    ignored = {each["kind"]: each for each in report["ignored"]}
    assert ignored["resources"]["labels"] == ["Robert", "Marie", "Jean", "Jeanine"]
    assert ignored["calendars"]["count"] == 10
    assert "4x10" in ignored["calendars"]["labels"]
    assert counted() == before


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_reimport_matches_by_lineage_then_by_uid_and_keeps_only_the_started_absent_tasks(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un planning exporté, retravaillé dans MS Project puis réimporté conserve […] les lignées
    # de ses tâches, et ses tâches démarrées. » A task without an identifier of Waterfall is
    # created, its identifier of MS Project kept.
    opened(api, stage)
    imported(
        api,
        stage,
        worker,
        planning(task(1, "Lot A"), task(2, "Tâche B"), task(3, "Tâche C"), task(4, "Tâche D")),
    )
    before = by_label(stage)
    set_progress(stage, str(before["Tâche C"][0].id), "started", date(2026, 11, 2))
    lineage = f"<GUID>{before['Lot A'][0].lineage_id}</GUID>"
    reworked = planning(
        task(10, "Lot A", besides=lineage),
        task(2, "Tâche B revue", level=2),
        task(5, "Tâche E"),
    )
    report = analysed(api, stage, worker, reworked)["report"]
    named = [
        (each["change"], each["label"], each["fields"])
        for each in report["differences"]
        if each["target"] == "task"
    ]
    assert named == [
        ("updated", "Tâche B revue", ["label", "parent"]),
        ("added", "Tâche E", []),
        ("kept", "Tâche C", []),
        ("removed", "Tâche D", []),
    ]
    assert (report["read_count"], report["unchanged_count"]) == (3, 1)
    applied(api, stage, worker, analysed(api, stage, worker, reworked))
    after = by_label(stage)
    assert set(after) == {"Lot A", "Tâche B revue", "Tâche C", "Tâche E"}
    for label, kept in (("Lot A", "Lot A"), ("Tâche B revue", "Tâche B"), ("Tâche C", "Tâche C")):
        assert after[label][0].lineage_id == before[kept][0].lineage_id
    assert after["Tâche B revue"][0].parent_id == after["Lot A"][0].id
    assert after["Tâche C"][1].progress == "started"
    assert (after["Tâche E"][1].external_id, after["Lot A"][1].external_id) == ("5", "1")


@pytest.mark.requirement("WF-INTF-0040-A")
@pytest.mark.requirement("WF-PLA-0030-A")
def test_the_links_of_the_file_replace_those_of_the_structure_each_change_presented(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Les liaisons […] du fichier remplacent celles de la structure, et le compte rendu
    # présente les liaisons ajoutées, modifiées et supprimées. »
    opened(api, stage)
    imported(
        api,
        stage,
        worker,
        planning(task(1, "A"), task(2, "B", besides=link(1)), task(3, "C", besides=link(2))),
    )
    reworked = planning(
        task(1, "A"),
        task(2, "B", besides=link(1, kind=3, lag=4800)),
        task(3, "C", besides=link(1, 0)),
    )
    report = analysed(api, stage, worker, reworked)["report"]
    assert [
        (each["change"], each["label"], each["predecessor_label"], each["fields"])
        for each in report["differences"]
    ] == [
        ("updated", "B", "A", ["predecessors"]),
        ("added", "C", "A", []),
        ("removed", "C", "B", []),
    ]
    applied(api, stage, worker, analysed(api, stage, worker, reworked))
    assert links(stage) == {
        ("A", "B", "start_to_start", Decimal(1), "d"),
        ("A", "C", "finish_to_finish", Decimal(0), "d"),
    }


@pytest.mark.requirement("WF-INTF-0040-A")
def test_an_order_item_task_moved_out_of_its_work_package_rejects_the_file_naming_both(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un fichier qui place la tâche d'un poste hors du sous-arbre de la tâche de son lot est
    # rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée a
    # disparu est appliqué et le compte rendu nomme le poste qu'elle portait ; une tâche
    # rattachée réimportée conserve son rattachement. »
    opened(api, stage)
    imported(api, stage, worker, planning(task(1, "Lot"), task(2, "Poste", level=2)))
    package, item = work_breakdown(stage)
    found = by_label(stage)
    package_task, item_task = found["Lot"][0].id, found["Poste"][0].id
    put_facts(stage, str(package_task), work_package_id=package)
    put_facts(stage, str(item_task), order_item_id=item)
    outside = analysed(api, stage, worker, planning(task(1, "Lot"), task(2, "Poste")))
    assert outside["report"]["refusals"] == [
        {
            "code": "ORDER_ITEM_OUTSIDE_WORK_PACKAGE",
            "params": {
                "work_package_task": {"node_id": str(package_task), "label": "Lot"},
                "order_item_tasks": [{"node_id": str(item_task), "label": "Poste"}],
            },
        }
    ]
    response = api.post(
        f"{path(stage, outside['import_id'])}/apply",
        headers=stage.manager.headers,
        json={"confirmed": True},
    )
    assert refusal(response)[2] == {"missing_condition": "import_file_accepted"}
    report = imported(api, stage, worker, planning(task(1, "Lot")))
    removed = [each for each in report["differences"] if each["change"] == "removed"]
    assert [(each["label"], each["work_breakdown_label"]) for each in removed] == [
        ("Poste", "Poste")
    ]
    assert by_label(stage)["Lot"][1].work_package_id == package


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_planning_of_sixteen_years_is_rejected_by_the_report_naming_its_task(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un import MS Project dont le planning s'étend sur seize ans est rejeté au compte rendu. »
    opened(api, stage)
    sixteen_years = Timing(duration=f"PT{16 * 366 * 24}H0M0S", unit="8")
    found = analysed(api, stage, worker, planning(task(1, "Exploitation", timing=sixteen_years)))
    assert found["report"]["refusals"] == [
        {
            "code": "PROJECT_HORIZON_EXCEEDED",
            "params": {"task": {"node_id": None, "label": "Exploitation"}},
        }
    ]
    assert found["report"]["date_mismatches"] == []


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_task_the_file_makes_a_milestone_over_a_started_subtask_is_rejected(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche » (#1772): the file
    # makes « Jalon » a milestone, and the import keeps its started subtask under it.
    opened(api, stage)
    imported(api, stage, worker, planning(task(1, "Jalon"), task(2, "Essais", level=2)))
    found = by_label(stage)
    set_progress(stage, str(found["Essais"][0].id), "started", date(2026, 11, 2))
    at_once = Timing(finish=f"{MONDAY}T08:00:00", duration="PT0H0M0S")
    report = imported(api, stage, worker, planning(task(1, "Jalon", timing=at_once)))
    named = {"lineage_id": str(found["Jalon"][0].lineage_id), "label": "Jalon"}
    assert report["rejected"] == [
        {"sheet": None, "row": 1, "code": "MILESTONE_HAS_NO_SUBTASK", "params": named}
    ]
    assert [each["change"] for each in report["differences"]] == ["kept"]
    after = by_label(stage)
    assert after["Essais"][0].parent_id == after["Jalon"][0].id


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_file_of_other_constants_is_imported_with_the_same_hours(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un fichier MS Project dont les constantes diffèrent de celles de l'installation est
    # importé avec les mêmes durées en heures. » Seven hours a day: « 2 j » is fourteen hours,
    # « 1 sem » thirty-five.
    opened(api, stage)
    week = link(1, lag=35 * 600, unit=9)
    content = planning(
        task(1, "Câblage", timing=Timing(duration="PT14H0M0S")),
        task(2, "Essais", besides=week),
        minutes=(420, 2100),
    )
    imported(api, stage, worker, content)
    cabling = by_label(stage)["Câblage"][1]
    assert (cabling.duration_value, cabling.duration_unit) == (Decimal("1.75"), "d")
    assert links(stage) == {("Câblage", "Essais", "finish_to_start", Decimal("0.875"), "w")}


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_file_that_is_no_planning_of_ms_project_is_refused_at_the_opening(
    api: ContractClient, stage: Scene
) -> None:
    opened(api, stage)
    response = opening(api, stage, b'<?xml version="1.0"?><Workbook xmlns="urn:other"/>')
    assert refusal(response) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {"expected_format": "ms_project_schedule"},
    )


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_file_whose_head_is_read_and_its_body_not_fails_its_analysis(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    opened(api, stage)
    broken = b'<Project xmlns="http://schemas.microsoft.com/project"><Tasks><Task>'
    response = opening(api, stage, broken)
    assert response.status_code == 202, response.text
    run(worker)
    assert read(api, stage, response.json()["import_id"])["status"] == "failed"


@pytest.mark.parametrize(
    ("head", "known"),
    [
        (b'<Project xmlns="http://schemas.microsoft.com/project">', True),
        (
            (
                b'\xef\xbb\xbf<?xml version="1.0"?>\n<!-- saved -->\n'
                b'<p:Project xmlns:p="http://schemas.microsoft.com/project/2007">'
            ),
            True,
        ),
        (b'<p:Project xmlns="http://schemas.microsoft.com/project">', False),
        (b'<Project xmlns="urn:other">', False),
        (b"<Projects/>", False),
        (b"PK\x03\x04", False),
    ],
)
def test_the_head_of_a_planning_is_a_project_of_the_namespace_of_ms_project(
    head: bytes, known: bool
) -> None:
    assert recognised(head) is known


def test_a_calendar_of_the_file_takes_the_days_it_does_not_list_from_its_base() -> None:
    # A night shift ends at midnight, the twenty-fourth hour; a calendar based on it sets one day.
    night = (
        "<WeekDay><DayType>{day}</DayType><DayWorking>1</DayWorking><WorkingTimes><WorkingTime>"
        "<FromTime>20:00:00</FromTime><ToTime>00:00:00</ToTime></WorkingTime></WorkingTimes>"
        "</WeekDay>"
    )
    calendars = (
        "<Calendars><Calendar><UID>1</UID><Name>Nuit</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<WeekDays>{''.join(night.format(day=day) for day in range(1, 8))}</WeekDays></Calendar>"
        "<Calendar><UID>2</UID><Name>Sans lundi</Name><BaseCalendarUID>1</BaseCalendarUID>"
        "<WeekDays><WeekDay><DayType>2</DayType><DayWorking>0</DayWorking></WeekDay></WeekDays>"
        "</Calendar></Calendars>"
    )
    content = (
        f'<Project xmlns="http://schemas.microsoft.com/project">{calendars}<Tasks/></Project>'
    ).encode()
    project = read_project(content).project
    resolved = calendars_of(project)
    assert resolved[1].calendar.week == (Decimal(4),) * 7
    assert resolved[2].calendar.week == (Decimal(0), *(Decimal(4),) * 6)
    assert resolved[1].instant(datetime.fromisoformat(f"{MONDAY}T22:00:00")) == instant(MONDAY, "2")
    defaults = constants_of(project)
    assert (defaults.hours_per_day, defaults.hours_per_week, defaults.days_per_month) == (
        Decimal(8),
        Decimal(40),
        Decimal(20),
    )
