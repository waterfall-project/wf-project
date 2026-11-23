# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a planning of MS Project beyond the bounds of the reader, or without a calendar.

Against the service, with the worker of the imports (US-3180): a hostile file fails its analysis
by the refusal of the format, never by an internal error nor after a report accepted; a file of
another tool, which names no calendar of its project, keeps its manual task at its dates. The
reader alone, without a database, is tried in ``test_msproject_bounds.py``.
"""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from imports_trial import import_worker, read, run
from nodes_support import opened
from projects_support import Scene
from projects_support import scene as make_scene
from support import ContractClient
from test_msproject_import import (
    MONDAY,
    Timing,
    analysed,
    applied,
    by_label,
    dates,
    instant,
    opening,
    task,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
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

pytestmark = pytest.mark.requirement("WF-INTF-0040-A")


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
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def file_of(*tasks: str, besides: str = "") -> bytes:
    """Write a planning of another tool than MS Project: no calendar, unless said besides."""
    return (
        '<Project xmlns="http://schemas.microsoft.com/project">'
        f"<StartDate>{MONDAY}T08:00:00</StartDate>{besides}<Tasks>{''.join(tasks)}</Tasks>"
        "</Project>"
    ).encode()


def on_levels(count: int, levels: int) -> list[str]:
    """Write tasks of a day going down the levels one by one, and again from the first."""
    return [task(uid, f"T{uid}", level=(uid - 1) % levels + 1) for uid in range(1, count + 1)]


HOSTILE = {
    "tasks": file_of(*on_levels(10_001, 1)),
    "levels": file_of(*on_levels(51, 51)),
    "integer": file_of(task(1, "A"), besides=f"<MinutesPerDay>{'4' * 19}</MinutesPerDay>"),
    "negative-unit": file_of(task(1, "A"), besides="<MinutesPerDay>-480</MinutesPerDay>"),
    "uid": file_of(task(int("9" * 201), "A")),
    "duration": file_of(task(1, "A", timing=Timing(duration=f"PT{'9' * 400}H"))),
}


@pytest.mark.parametrize("hostile", HOSTILE)
def test_a_file_beyond_the_bounds_of_the_reader_fails_its_analysis_as_an_unreadable_format(
    api: ContractClient, stage: Scene, worker: Worker, hostile: str
) -> None:
    # « Au-delà de 10 000 tâches ou de 50 niveaux, l'import échoue à l'analyse sur
    # FILE_FORMAT_UNREADABLE, expected_format à ms_project_schedule, sans que le moteur ne soit
    # rejoué. De même une durée que le lecteur ne peut pas porter (PT999…H) et un entier au-delà de
    # la borne de chiffres du lecteur, dont un UID que external_id ne garderait pas. Aucun de ces
    # fichiers ne finit en INTERNAL_ERROR, et aucun n'échoue après un compte rendu accepté. »
    opened(api, stage)
    response = opening(api, stage, HOSTILE[hostile])
    assert response.status_code == 202, response.text
    run(worker)
    failed = read(api, stage, response.json()["import_id"])
    assert (failed["status"], failed["report"]) == ("failed", None)
    assert failed["task"]["problem"]["code"] == "FILE_FORMAT_UNREADABLE"
    assert failed["task"]["problem"]["params"] == {"expected_format": "ms_project_schedule"}


def test_a_planning_of_10_000_tasks_on_50_levels_is_analysed(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un planning de 10 000 tâches sur 50 niveaux est accepté » : the engine is replayed through
    # its fifty levels of summaries without exhausting its recursion.
    opened(api, stage)
    found = analysed(api, stage, worker, file_of(*on_levels(10_000, 50)))
    assert found["report"]["read_count"] == 10_000
    assert found["report"]["refusals"] == []


@pytest.mark.parametrize(
    "besides", ["", "<CalendarUID>7</CalendarUID>"], ids=["names-none", "names-one-absent"]
)
def test_a_manual_task_of_a_file_without_its_calendar_keeps_its_dates_and_is_compared(
    api: ContractClient, stage: Scene, worker: Worker, besides: str
) -> None:
    # « Un fichier qui ne nomme pas le calendrier de son projet, ou qui nomme un calendrier qu'il ne
    # porte pas, se lit sur le calendrier « Standard » de MS Project, comme l'écart de calendrier le
    # fait déjà ; sa tâche manuelle, ou à contrainte de date, est en mode manuel aux dates du
    # fichier, et date_mismatches compare ses dates. » Standard is the default calendar of eight
    # hours: ten o'clock is the second hour of work, two in the afternoon the fifth; the automatic
    # task the file dates on Wednesday starts on Monday by the engine, and the report says so.
    opened(api, stage)
    tuesday = Timing("2026-11-03T10:00:00", "2026-11-03T14:00:00", "PT3H0M0S", "5")
    wednesday = Timing("2026-11-04T08:00:00", "2026-11-04T17:00:00")
    content = file_of(
        task(1, "Revue", besides="<Manual>1</Manual>", timing=tuesday),
        task(2, "Contrainte", besides="<ConstraintType>4</ConstraintType>", timing=tuesday),
        task(3, "Rédaction", timing=wednesday),
        besides=besides,
    )
    found = analysed(api, stage, worker, content)
    assert found["report"]["signals"] == []
    assert [(each["label"], each["fields"]) for each in found["report"]["date_mismatches"]] == [
        ("Rédaction", ["start", "finish"])
    ]
    applied(api, stage, worker, found)
    kept = by_label(stage)
    for label in ("Revue", "Contrainte"):
        assert (kept[label][1].scheduling_mode, dates(kept[label][1])) == (
            "manual",
            (instant("2026-11-03", "2"), instant("2026-11-03", "5")),
        )
    assert kept["Rédaction"][1].scheduling_mode == "automatic"
