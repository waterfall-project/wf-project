# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a planning of MS Project in calendar gap: its report, its two rules (US-2000/L2).

Against the service, with the worker of the imports, on the synthetic planning 14 of the corpus
(``fixtures/msproject``), written for these tests and entered in days of seven hours: its
« Standard » from 8:00 to 12:00 and from 13:00 to 16:00, its constants 7, 35 and 20, and the own
calendar « Atelier » of « Peinture » and « Fabrication », nine hours from Monday to Thursday. The
installation counts 8, 40 and 20, its default calendar eight hours from Monday to Friday. The
report says the gap; keeping the durations, the default, a duration in days or weeks keeps its
value in its unit; keeping the dates, an automatic task lasts the work between its dates of the
file on its Waterfall calendar; ``setImportDurationRule`` changes the rule and analyses again.
"""

from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from imports_trial import deposited, import_worker, path, read, refusal, run
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_import import (
    CORPUS,
    Timing,
    by_label,
    corpus,
    dates,
    instant,
    link,
    links,
    planning,
    task,
    tasks,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.planning.calendar_gap import calendar_gap, placed_on
from waterfall.core.planning.calendars import Applicable
from waterfall.core.planning.msproject import MsProject, clock_text
from waterfall.core.planning.scheduling import WorkInstant, weekly_calendar
from waterfall.core.resource_settings.tables import Calendar as CalendarRow
from waterfall.platform.database import utc_now
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

KIND = "ms_project_schedule"
SYNTHETIC = "14-calendar-gap-seven-hours.xml"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def week(*hours: str) -> dict[str, str]:
    """Give the hours of each day of a week, Monday first."""
    return dict(zip(DAYS, hours, strict=True))


def times(*periods: tuple[str, str], days: int) -> dict[str, list[dict[str, str]]]:
    """Give the working times of a calendar of the file: the same periods its first ``days``."""
    day = [{"from": start, "to": end} for start, end in periods]
    return {name: day if rank < days else [] for rank, name in enumerate(DAYS)}


STANDARD = {
    "name": "Standard",
    "weekly_hours": week("7", "7", "7", "7", "7", "0", "0"),
    "working_times": times(("08:00", "12:00"), ("13:00", "16:00"), days=5),
}
WORKSHOP = {
    "name": "Atelier",
    "weekly_hours": week("9", "9", "9", "9", "0", "0", "0"),
    "working_times": times(("08:00", "12:00"), ("13:00", "18:00"), days=4),
}
EIGHT_HOURS = week("8", "8", "8", "8", "8", "0", "0")
# The durations each task keeps under each rule, by its label: its value and its unit.
KEPT_DURATIONS = {
    "Études": (Decimal(2), "d"),
    "Peinture": (Decimal(1), "d"),
    "Câblage": (Decimal(56), "h"),
    "Fabrication": (Decimal(4), "d"),
    "Recette": (Decimal(1), "w"),
    "Séchage": (Decimal(2), "ed"),
    "Livraison": (Decimal(1), "d"),
}
KEPT_DATES = {
    **KEPT_DURATIONS,
    # From the Tuesday at 16:00, seven of the nine hours of « Atelier », to the Wednesday at 14:00,
    # five of nine: the same shares of eight hours, 56/9 hours, 7/9 of a day.
    "Peinture": (Decimal("0.7777777778"), "d"),
    # Eight whole days of the file, from the 5th to the 16th of March: eight days of eight hours.
    "Câblage": (Decimal(64), "h"),
    # From the Monday at 8:00 to the Thursday at 9:00 of « Atelier », one of nine hours.
    "Fabrication": (Decimal("3.1111111111"), "d"),
}


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
    """Give a platform whose default calendar works eight hours from Monday to Friday."""
    found = make_scene(api, owner, database, realm)
    eight, none = Decimal(8), Decimal(0)
    with owner.begin() as connection:
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
    return found


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def analysed(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> dict[str, Any]:
    """Open the import of a planning as the manager does and run its analysis; give it."""
    upload_id = deposited(api, stage.manager, content)
    response = api.post(
        path(stage), headers=stage.manager.headers, json={"kind": KIND, "upload_id": upload_id}
    )
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, response.json()["import_id"])
    assert found["status"] == "analysed", found
    return found


def ruled(api: ContractClient, stage: Scene, import_id: str, rule: str, who: Any = None) -> Any:
    """Ask for a rule of the durations of an import; give the answer."""
    return api.put(
        f"{path(stage, import_id)}/duration-rule",
        headers=(who or stage.manager).headers,
        json={"duration_rule": rule},
    )


def applied(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> None:
    """Confirm the application of an import analysed, and run it to its end."""
    response = api.post(
        f"{path(stage, import_id)}/apply", headers=stage.manager.headers, json={"confirmed": True}
    )
    assert response.status_code == 202, response.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


def kept_dates(api: ContractClient, stage: Scene, worker: Worker) -> dict[str, Any]:
    """Analyse the synthetic planning, then again keeping its dates; give the import analysed."""
    import_id = analysed(api, stage, worker, corpus(SYNTHETIC))["import_id"]
    response = ruled(api, stage, import_id, "keep_dates")
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "analysed", found
    return found


def durations(stage: Scene) -> dict[str, tuple[Decimal, str]]:
    """Read the duration of each task of the main structure, by its label."""
    return {
        each.label: (each.duration_value.normalize(), each.duration_unit)
        for _, each in tasks(stage)
    }


def mismatched(report: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Give the tasks whose dates differ from the file's, each with what differs."""
    return [(each["label"], each["fields"]) for each in report["date_mismatches"]]


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_planning_entered_on_other_days_says_its_calendar_gap_before_the_confirmation(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « Un fichier MS Project dont les constantes ou le calendrier diffèrent de ceux de
    # l'installation est signalé au compte rendu » : before the confirmation, the hours per day on
    # either side, the working times of the file, each task whose own calendar differs from its
    # Waterfall one; the calendars of the file still not imported, and said ignored.
    found = analysed(api, stage, worker, corpus(SYNTHETIC))
    report = found["report"]
    with database.transaction() as session:
        default = session.scalars(select(CalendarRow).where(CalendarRow.is_default)).one()
        calendar_id, label = str(default.id), default.label
    assert report["unit_constants"] == {
        "file": {"hours_per_day": "7", "hours_per_week": "35", "days_per_month": "20"},
        "installation": {"hours_per_day": "8", "hours_per_week": "40", "days_per_month": "20"},
    }
    assert report["calendar_gap"] == {
        "project_calendar": STANDARD,
        "installation_calendar": {
            "calendar_id": calendar_id,
            "label": label,
            "weekly_hours": EIGHT_HOURS,
        },
        "tasks": [
            {
                "lineage_id": None,
                "label": name,
                "file_calendar": WORKSHOP,
                "weekly_hours": EIGHT_HOURS,
            }
            for name in ("Peinture", "Fabrication")
        ],
        "duration_rule": "keep_durations",
    }
    assert report["ignored"] == [
        {"kind": "calendars", "count": 2, "labels": ["Standard", "Atelier"]}
    ]
    added = [each["label"] for each in report["differences"] if each["target"] == "task"]
    assert added == [
        "Études",
        "Peinture",
        "Câblage",
        "Fabrication",
        "Recette",
        "Séchage",
        "Livraison",
    ]
    assert (report["rejected"], report["refusals"], report["signals"]) == ([], [], [])
    with database.transaction() as session:
        row = session.get_one(ImportReport, UUID(found["import_id"]))
        assert row.duration_rule == "keep_durations"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_keeping_the_durations_a_task_of_two_days_entered_at_seven_hours_lasts_two_days(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Importé en gardant les durées, une tâche de « 2 j » saisie à 7 h par jour vaut deux jours,
    # soit seize heures avec les valeurs par défaut » : a duration or a lag in days or weeks keeps
    # its value in its unit, one in hours its hours, one in elapsed time is not concerned; a manual
    # task keeps the dates of the file. Waterfall dates the others on its calendars, and the dates
    # that move are presented: « Peinture » cannot start the Tuesday « Études » now fills,
    # « Câblage » of 56 hours ends a day earlier on days of eight, « Recette » starts the day after
    # « Fabrication » ends, and « Séchage » follows « Câblage ».
    found = analysed(api, stage, worker, corpus(SYNTHETIC))
    assert mismatched(found["report"]) == [
        ("Peinture", ["start"]),
        ("Câblage", ["finish"]),
        ("Recette", ["start"]),
        ("Séchage", ["start", "finish"]),
    ]
    applied(api, stage, worker, found["import_id"])
    assert durations(stage) == KEPT_DURATIONS
    assert ("Études", "Câblage", "finish_to_start", Decimal(1), "d") in links(stage)
    found_tasks = by_label(stage)
    # « 2 j » is sixteen hours: from the Monday morning to the end of the Tuesday.
    assert dates(found_tasks["Études"][1]) == (
        instant("2026-03-02", "0"),
        instant("2026-03-03", "8"),
    )
    delivery = found_tasks["Livraison"][1]
    assert (delivery.scheduling_mode, dates(delivery)) == (
        "manual",
        (instant("2026-03-20", "0"), instant("2026-03-20", "7")),
    )


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.requirement("WF-INTF-0080-A")
def test_keeping_the_dates_an_automatic_task_lasts_the_work_between_its_dates_of_the_file(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Importé en gardant les dates, sa durée est le temps de travail entre ses dates du fichier
    # sur son calendrier Waterfall. » In the unit of its duration at the constants of the
    # installation; the lag of « Câblage » keeps its day, the elapsed « Séchage » its two days, the
    # manual « Livraison » its dates. What the engine still moves is presented: « Peinture » cannot
    # start the Tuesday « Études » fills on days of eight hours.
    found = kept_dates(api, stage, worker)
    report = found["report"]
    assert report["calendar_gap"]["duration_rule"] == "keep_dates"
    assert mismatched(report) == [("Peinture", ["start"])]
    applied(api, stage, worker, found["import_id"])
    assert durations(stage) == KEPT_DATES
    assert ("Études", "Câblage", "finish_to_start", Decimal(1), "d") in links(stage)
    days = {label: (start.day, finish.day) for label, (start, finish) in _dates(stage).items()}
    assert days == {
        "Études": (date(2026, 3, 2), date(2026, 3, 3)),
        "Peinture": (date(2026, 3, 4), date(2026, 3, 4)),
        "Câblage": (date(2026, 3, 5), date(2026, 3, 16)),
        "Fabrication": (date(2026, 3, 2), date(2026, 3, 5)),
        "Recette": (date(2026, 3, 5), date(2026, 3, 12)),
        "Séchage": (date(2026, 3, 17), date(2026, 3, 19)),
        "Livraison": (date(2026, 3, 20), date(2026, 3, 20)),
    }


def _dates(stage: Scene) -> dict[str, tuple[Any, Any]]:
    """Read the dates of each task of the main structure, by its label."""
    return {each.label: dates(each) for _, each in tasks(stage)}


@pytest.mark.requirement("WF-INTF-0080-A")
def test_changing_the_option_gives_a_new_report_and_abandoning_then_leaves_the_project_as_it_was(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « Pour un planning MS Project saisi sur un autre calendrier, le compte rendu propose de garder
    # les durées ou les dates ; changer d'option rend un nouveau compte rendu, et le projet reste
    # inchangé jusqu'à la confirmation. » « Si l'utilisateur abandonne à cette étape, le projet
    # reste inchangé » — after a change of option too.
    first = analysed(api, stage, worker, corpus(SYNTHETIC))
    import_id = first["import_id"]
    changed = ruled(api, stage, import_id, "keep_dates")
    assert changed.status_code == 202, changed.text
    answer = changed.json()
    assert (answer["status"], answer["report"], answer["expires_at"]) == ("analysing", None, None)
    assert answer["task"]["task_id"] != first["task"]["task_id"]
    # A replay while the analysis runs, after a lost answer, is refused: the client reads it again.
    assert refusal(ruled(api, stage, import_id, "keep_dates")) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "import_awaiting_decision"},
    )
    assert tasks(stage) == []
    run(worker)
    second = read(api, stage, import_id)
    assert second["report"]["calendar_gap"]["duration_rule"] == "keep_dates"
    assert second["report"]["date_mismatches"] != first["report"]["date_mismatches"]
    assert tasks(stage) == []
    # Back to the durations kept, the report is the first one again.
    assert ruled(api, stage, import_id, "keep_durations").status_code == 202
    run(worker)
    assert read(api, stage, import_id)["report"] == first["report"]
    assert api.delete(path(stage, import_id), headers=stage.manager.headers).status_code == 204
    assert read(api, stage, import_id)["status"] == "abandoned"
    assert tasks(stage) == []
    with database.transaction() as session:
        assert session.get_one(ImportReport, UUID(import_id)).duration_rule == "keep_durations"


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_rule_the_report_was_computed_under_gives_the_import_back_as_it_stands(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Changer d'option rend un nouveau compte rendu » : the option already in place changes
    # nothing — no new analysis, the same report, the same task (200).
    found = analysed(api, stage, worker, corpus(SYNTHETIC))
    response = ruled(api, stage, found["import_id"], "keep_durations")
    assert response.status_code == 200, response.text
    assert response.json() == found
    assert not worker.step()


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_rule_of_an_import_is_refused_to_who_may_not_apply_it_and_on_an_unknown_import(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # As for applying it: an import of a project the caller may not consult does not exist (404);
    # without the permission of its kind, 403 naming it; an unknown import, 404.
    import_id = analysed(api, stage, worker, corpus(SYNTHETIC))["import_id"]
    assert refusal(ruled(api, stage, import_id, "keep_dates", stage.outsider))[:2] == (
        404,
        "NOT_FOUND",
    )
    assert refusal(ruled(api, stage, import_id, "keep_dates", stage.reader)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "planning.write"},
    )
    assert refusal(ruled(api, stage, str(uuid4()), "keep_dates"))[:2] == (404, "NOT_FOUND")
    assert read(api, stage, import_id)["report"]["calendar_gap"]["duration_rule"] == (
        "keep_durations"
    )


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.parametrize("body", [{"duration_rule": "foo"}, {}], ids=["unknown rule", "no rule"])
def test_a_rule_that_is_not_one_of_the_two_is_refused_as_a_field_invalid(
    api: ContractClient, stage: Scene, worker: Worker, body: dict[str, Any]
) -> None:
    # The body is judged by the contract before the import: a value out of the two, or none, is a
    # field refused, 422 ``VALIDATION_FAILED`` (the 400 is for a body that is no JSON), and the
    # report stays as it was.
    found = analysed(api, stage, worker, corpus(SYNTHETIC))
    response = api.put(
        f"{path(stage, found['import_id'])}/duration-rule",
        headers=stage.manager.headers,
        json=body,
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert [each["pointer"] for each in response.json()["fields"]] == ["/duration_rule"]
    assert read(api, stage, found["import_id"]) == found
    assert not worker.step()


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_rule_of_an_import_applied_or_expired_is_refused_as_no_longer_awaiting_a_decision(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # As for applying it: an import no longer analysed — applied, expired — is refused by the 409
    # ``import_awaiting_decision``, and nothing is analysed again.
    awaiting = {"missing_condition": "import_awaiting_decision"}
    done = analysed(api, stage, worker, corpus(SYNTHETIC))["import_id"]
    applied(api, stage, worker, done)
    assert refusal(ruled(api, stage, done, "keep_dates")) == (
        409,
        "STATE_FORBIDS_OPERATION",
        awaiting,
    )
    lapsed = analysed(api, stage, worker, corpus(SYNTHETIC))["import_id"]
    with database.transaction() as session:
        session.execute(
            update(ImportReport)
            .where(ImportReport.id == UUID(lapsed))
            .values(expires_at=utc_now() - timedelta(seconds=1))
        )
    assert read(api, stage, lapsed)["status"] == "expired"
    assert refusal(ruled(api, stage, lapsed, "keep_dates")) == (
        409,
        "STATE_FORBIDS_OPERATION",
        awaiting,
    )
    assert not worker.step()


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_file_of_the_corpus_that_says_constants_differ_says_a_calendar_gap_too(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # The constants that differ are said in a gap, which offers the choice of the rule: on every
    # file of the corpus, ``unit_constants`` set implies ``calendar_gap`` set.
    for file in sorted(CORPUS.glob("*.xml")):
        upload_id = deposited(api, stage.manager, file.read_bytes())
        response = api.post(
            path(stage), headers=stage.manager.headers, json={"kind": KIND, "upload_id": upload_id}
        )
        assert response.status_code == 202, response.text
        run(worker)
        report = read(api, stage, response.json()["import_id"])["report"]
        if report is not None and report["unit_constants"] is not None:
            assert report["calendar_gap"] is not None, file.name


@pytest.mark.requirement("WF-PLA-0160-A")
def test_keeping_the_dates_a_task_of_two_days_at_seven_hours_on_days_of_eight_lasts_its_hours(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Importé en gardant les dates, sa durée est le temps de travail entre ses dates du fichier
    # sur son calendrier Waterfall. » « 2 j » at seven hours a day on a calendar of eight hours, in
    # gap by its constants alone: from the Monday at 8:00 to the Tuesday at 15:00, fourteen hours
    # of the calendar of eight, 1.75 days; its lag of « 1 sem » keeps its week.
    content = planning(
        task(1, "Câblage", timing=Timing(finish="2026-11-03T15:00:00", duration="PT14H0M0S")),
        task(2, "Essais", besides=link(1, lag=35 * 600, unit=9)),
        minutes=(420, 2100),
    )
    import_id = analysed(api, stage, worker, content)["import_id"]
    assert ruled(api, stage, import_id, "keep_dates").status_code == 202
    run(worker)
    applied(api, stage, worker, import_id)
    assert durations(stage)["Câblage"] == (Decimal("1.75"), "d")
    assert links(stage) == {("Câblage", "Essais", "finish_to_start", Decimal(1), "w")}


@pytest.mark.requirement("WF-PLA-0160-A")
def test_an_hour_of_the_clock_carries_its_seconds_only_when_it_has_some() -> None:
    # ``ImportWorkingTime``: ``HH:MM``, ``HH:MM:SS`` on a second, the end of the day ``24:00``.
    assert [clock_text(each) for each in (Fraction(8), Fraction(49, 6), Fraction(24))] == [
        "08:00",
        "08:10",
        "24:00",
    ]
    assert clock_text(Fraction(8) + Fraction(1, 3600)) == "08:00:01"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_file_that_names_no_calendar_of_its_project_is_on_the_one_ms_project_assumes() -> None:
    # MS Project dates such a file from 8:00 to 12:00 and from 13:00 to 17:00, Monday to Friday:
    # no gap with a default calendar of eight hours from Monday to Friday, a gap with one of seven.
    project = MsProject(start=None)
    eight = Applicable(uuid4(), weekly_calendar([Decimal(h) for h in (8, 8, 8, 8, 8, 0, 0)]))
    seven = Applicable(uuid4(), weekly_calendar([Decimal(h) for h in (7, 7, 7, 7, 7, 0, 0)]))
    assert calendar_gap(project, {}, (False, (eight, "Huit")), [], "keep_durations") is None
    gap = calendar_gap(project, {}, (False, (seven, "Sept")), [], "keep_dates")
    assert gap is not None
    assert gap["project_calendar"]["name"] is None
    assert gap["project_calendar"]["working_times"]["friday"] == [
        {"from": "08:00", "to": "12:00"},
        {"from": "13:00", "to": "17:00"},
    ]
    assert gap["duration_rule"] == "keep_dates"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_an_instant_on_a_day_without_hours_in_the_file_starts_its_day_on_a_waterfall_one() -> None:
    # Kept dates place an instant of the file at the same share of the work of its day: a day the
    # file does not work has no share, and the instant is the start of the day.
    saturday = WorkInstant(date(2026, 3, 7), Decimal(0))
    on_file = weekly_calendar([Decimal(h) for h in (7, 7, 7, 7, 7, 0, 0)])
    every_day = weekly_calendar([Decimal(8)] * 7)
    moment = placed_on(saturday, on_file, every_day)
    assert (moment.ordinal, moment.hours) == (saturday.day.toordinal(), Fraction(0))
