# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals and the readings of a planning of MS Project at its import (US-1430/L3).

The second half of the tests of the import: what the report rejects or signals — the limits, the
other constants, the labels, the summaries and the leaves, the loops, the files that are no
planning —, against the service with the worker of the imports. The helpers and the first half
are in ``test_msproject_import.py``.
"""

import time
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from imports_trial import import_worker, read, refusal, run
from nodes_support import opened, set_progress
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from support import ContractClient
from test_msproject_import import (
    MONDAY,
    Timing,
    analysed,
    by_label,
    corpus,
    imported,
    instant,
    link,
    links,
    main_structure,
    opening,
    planning,
    seven_hours_a_day,
    task,
    tasks,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.planning.msproject import calendars_of, constants_of, read_project, recognised
from waterfall.platform.keycloak_admin import KeycloakAdmin

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
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


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
def test_a_file_of_other_constants_is_signalled_and_keeps_its_durations_in_their_unit(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un fichier MS Project dont les constantes ou le calendrier diffèrent de ceux de
    # l'installation est signalé au compte rendu ; importé en gardant les durées, une tâche de
    # « 2 j » saisie à 7 h par jour vaut deux jours, soit seize heures avec les valeurs par
    # défaut ; » Seven hours a day, on the calendar of the installation: in calendar gap by its
    # constants alone, which ``unit_constants`` gives and ``calendar_gap`` never leaves without its
    # rule (#3129). « 1 sem » of thirty-five hours stays a week.
    opened(api, stage)
    week = link(1, lag=35 * 600, unit=9)
    content = planning(
        task(1, "Câblage", timing=Timing(duration="PT14H0M0S")),
        task(2, "Essais", besides=week),
        minutes=(420, 2100),
    )
    report = imported(api, stage, worker, content)
    assert report["unit_constants"] == {
        "file": {"hours_per_day": "7", "hours_per_week": "35", "days_per_month": "20"},
        "installation": {"hours_per_day": "8", "hours_per_week": "40", "days_per_month": "20"},
    }
    gap = report["calendar_gap"]
    assert gap is not None
    assert (gap["duration_rule"], gap["tasks"]) == ("keep_durations", [])
    cabling = by_label(stage)["Câblage"][1]
    assert (cabling.duration_value.normalize(), cabling.duration_unit) == (Decimal(2), "d")
    assert links(stage) == {("Câblage", "Essais", "finish_to_start", Decimal(1), "w")}


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.requirement("WF-QUA-0080-A")
def test_the_report_of_the_planning_of_other_constants_signals_the_difference(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un fichier MS Project dont les constantes ou le calendrier diffèrent de ceux de
    # l'installation est signalé au compte rendu » : the file 10 of the corpus carries 7 hours a
    # day, 35 a week and 20 days a month; the installation 8, 40 and 20. Its « Standard » of six
    # hours a day is not the default calendar either: the file is in calendar gap.
    seven_hours_a_day(stage)
    report = analysed(api, stage, worker, corpus("10-other-constants.xml"))["report"]
    assert report["unit_constants"] == {
        "file": {"hours_per_day": "7", "hours_per_week": "35", "days_per_month": "20"},
        "installation": {"hours_per_day": "8", "hours_per_week": "40", "days_per_month": "20"},
    }
    assert report["calendar_gap"] is not None
    assert report["calendar_gap"]["project_calendar"]["weekly_hours"]["monday"] == "6"
    assert report["refusals"] == []


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_task_without_a_label_or_with_too_long_a_one_is_rejected_its_subtasks_rising(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # A rejected line is named by its row, the others apply: the subtask of a task the file
    # would create without a label rises to its parent.
    opened(api, stage)
    content = planning(
        task(1, " "), task(2, "Câblage", level=2), task(3, "x" * 301), task(4, "Essais")
    )
    report = imported(api, stage, worker, content)
    assert report["rejected"] == [
        {"sheet": None, "row": 1, "code": "VALUE_REQUIRED", "params": {}},
        {"sheet": None, "row": 3, "code": "VALUE_TOO_LONG", "params": {"max_length": 300}},
    ]
    assert (report["read_count"], report["unchanged_count"]) == (4, 0)
    assert [(node.parent_id, task.label) for node, task in tasks(stage)] == [
        (None, "Câblage"),
        (None, "Essais"),
    ]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_the_file_makes_a_leaf_takes_its_duration_and_keeps_its_state(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une récapitulative qui perd sa dernière subordonnée devient une tâche feuille en mode
    # automatique […], conserve son état. » Its started subtask moves out of it.
    opened(api, stage)
    imported(api, stage, worker, planning(task(1, "Études"), task(2, "Conception", level=2)))
    set_progress(stage, str(by_label(stage)["Conception"][0].id), "started", date(2026, 11, 2))
    report = imported(
        api,
        stage,
        worker,
        planning(task(1, "Études", timing=Timing(duration="PT16H0M0S")), task(2, "Conception")),
    )
    assert [(each["label"], each["fields"]) for each in report["differences"]] == [
        ("Études", ["duration"]),
        ("Conception", ["parent"]),
    ]
    studies = by_label(stage)["Études"][1]
    assert (studies.progress, studies.duration_value, studies.duration_unit) == (
        "started",
        Decimal(2),
        "d",
    )


@pytest.mark.story("US-3310")
def test_a_leaf_started_the_file_gives_a_subtask_is_a_summary_started_at_its_date(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # La règle vaut quelle que soit l'entrée, l'import MS Project (``applyImport``) compris : le
    # fichier donne à « Études », démarrée le 1er mars 2026, une sous-tâche non démarrée ; l'import
    # ne la refuse pas, et « Études » est une récapitulative démarrée à sa date.
    revision = opened(api, stage)
    imported(api, stage, worker, planning(task(1, "Études")))
    set_progress(stage, str(by_label(stage)["Études"][0].id), "started", date(2026, 3, 1))
    report = imported(
        api, stage, worker, planning(task(1, "Études"), task(2, "Conception", level=2))
    )
    assert report["rejected"] == []
    node, _ = by_label(stage)["Études"]
    assert by_label(stage)["Conception"][0].parent_id == node.id
    base = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"
    listed = api.get(
        f"{base}/structures/{main_structure(stage)}/nodes", headers=stage.manager.headers
    )
    assert listed.status_code == 200, listed.text
    studies = next(each for each in listed.json()["items"] if each["node_id"] == str(node.id))
    assert studies["task"]["is_summary"] is True
    assert (studies["task"]["progress"], studies["task"]["started_on"]) == ("started", "2026-03-01")


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_file_whose_links_close_a_loop_fails_its_analysis(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    opened(api, stage)
    loop = planning(task(1, "A", besides=link(2)), task(2, "B", besides=link(1)))
    response = opening(api, stage, loop)
    assert response.status_code == 202, response.text
    run(worker)
    failed = read(api, stage, response.json()["import_id"])
    assert failed["status"] == "failed"
    problem = failed["task"]["problem"]
    assert problem["code"] == "LINK_CYCLE"
    assert sorted(each["label"] for each in problem["params"]["cycle"]) == ["A", "B"]


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
    failed = read(api, stage, response.json()["import_id"])
    assert failed["status"] == "failed"
    assert failed["task"]["problem"]["code"] == "FILE_FORMAT_UNREADABLE"
    assert failed["task"]["problem"]["params"] == {"expected_format": "ms_project_schedule"}


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
        (b"<!---->" * 500 + b"<x", False),
        (b"<?a?>" * 800 + b"<x", False),
        (b"<!---->" * 500 + b'<Project xmlns="http://schemas.microsoft.com/project">', True),
    ],
)
@pytest.mark.requirement("WF-INTF-0040-A")
def test_the_head_of_a_planning_is_a_project_of_the_namespace_of_ms_project(
    head: bytes, known: bool
) -> None:
    started = time.monotonic()
    assert recognised(head) is known
    assert time.monotonic() - started < 1  # no backtracking on a head of 4 096 bytes


@pytest.mark.requirement("WF-PLA-0010-A")
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
