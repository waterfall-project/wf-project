# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The status screen, ``getSystemStatus``: what it reads of Prometheus, the database, the settings.

The application runs on the database of the test and the realm of test, and reads the metrics from
a Prometheus of the test (``prometheus_support``), which answers what each test says the metrics
hold — the API's own exposition is the subject of ``test_metrics.py``, the rules of the alerts that
of the tests of the chart and the Compose. Every answer is checked against the contract.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from installed_reference import holding, install
from prometheus_support import TestPrometheus
from sqlalchemy import insert
from support import ContractClient, nowhere

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.status import UNMEASURED, StatusSources, alert, fullest
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.prometheus import (
    AVAILABILITY,
    AVAILABLE,
    CHECKED,
    USED,
    VERSIONS,
    FiringAlert,
    Prometheus,
    PrometheusError,
    Space,
)
from waterfall.platform.settings import OperatingParameters
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import ServiceSettings

STATUS = "/api/v1/system/status"
CHECKED_AT = datetime(2026, 6, 3, 14, 4, 30, tzinfo=UTC)
COMPONENTS = ("api", "worker", "database", "cache", "object_storage", "identity_provider")
VERSIONS_SAID = {"api": __version__, "worker": __version__, "database": "18.1", "cache": "8.2.1"}
CORRELATION = "01926f3a-7c00-7000-8000-000000001983"
GIB = 1024**3


@pytest.fixture
def prometheus() -> Iterator[TestPrometheus]:
    served = TestPrometheus()
    yield served
    served.stop()


def screen_on(
    contract: OpenAPI,
    services: Services,
    prometheus: TestPrometheus | None,
    parameters: OperatingParameters | None = None,
) -> ContractClient:
    client = None if prometheus is None else Prometheus(prometheus.address)
    sources = StatusSources(parameters or OperatingParameters(), client)
    app = create_app(services, sources=sources)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def platform(
    database: Database, keycloak: Keycloak, realm_settings: ServiceSettings, owner: Engine
) -> Services:
    """Give the services of an installation bootstrapped on the database and the realm of test."""
    install(owner)
    return Services(database, keycloak, KeycloakAdmin(keycloak, realm_settings), *nowhere())


@pytest.fixture
def viewer(database: Database, realm: TestRealm) -> dict[str, str]:
    """Give the session of an account that may view the status and is contributor to no project."""
    return holding(database, realm, "system_status.read")


def collected(
    prometheus: TestPrometheus,
    at: datetime = CHECKED_AT,
    *,
    down: tuple[str, ...] = (),
) -> None:
    """Make the metrics say every component collected at a moment, those named down."""
    prometheus.holds(
        AVAILABILITY, [({"component": c}, 0.0 if c in down else 1.0) for c in COMPONENTS]
    )
    prometheus.holds(CHECKED, [({"component": c}, at.timestamp()) for c in COMPONENTS])
    prometheus.holds(
        VERSIONS, [({"component": c, "version": v}, 1.0) for c, v in VERSIONS_SAID.items()]
    )
    prometheus.holds(
        USED, [({"component": "database"}, 39.0 * GIB), ({"component": "object_storage"}, GIB)]
    )
    prometheus.holds(
        AVAILABLE,
        [({"component": "database"}, 161.0 * GIB), ({"component": "object_storage"}, 99.0 * GIB)],
    )


def ended_task(database: Database, kind: str, at: datetime, *, succeeded: bool) -> None:
    """Write a task of the platform ended at a moment, its problem when it failed."""
    problem = {
        "code": "COMPONENT_UNAVAILABLE",
        "status": 503,
        "params": {"component": "object_storage"},
        "correlation_id": CORRELATION,
    }
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=uuid4(),
                kind=kind,
                status="succeeded" if succeeded else "failed",
                progress=100 if succeeded else 0,
                payload={},
                problem=None if succeeded else problem,
                correlation_id=CORRELATION,
                attempts=1,
                submitted_at=at - timedelta(minutes=5),
                started_at=at - timedelta(minutes=4),
                finished_at=at,
            )
        )


def read(screen: ContractClient, viewer: dict[str, str]) -> dict[str, Any]:
    answer = screen.get(STATUS, headers=viewer)
    assert answer.status_code == 200, answer.text
    return answer.json()


def by_component(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {each["component"]: each for each in status["components"]}


@pytest.mark.requirement("WF-ADM-0130-A")
def test_a_component_stopped_appears_on_the_screen_at_the_next_check(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'arrêt d'un composant apparaît sur l'écran d'état à la vérification suivante. » : each
    # component presented, in the order of the contract, with the date of its last collection; the
    # database stopped at the next collection is said unavailable, at that collection's date.
    screen = screen_on(contract, platform, prometheus)
    collected(prometheus)
    before = by_component(read(screen, viewer))
    assert list(before) == [*COMPONENTS, "metrics"]
    assert all(each["is_available"] for each in before.values())
    assert before["database"]["checked_at"] == "2026-06-03T14:04:30Z"
    later = CHECKED_AT + timedelta(seconds=15)
    collected(prometheus, later, down=("database",))
    after = by_component(read(screen, viewer))
    assert after["database"]["is_available"] is False
    assert after["database"]["checked_at"] == "2026-06-03T14:04:45Z"
    assert [c for c, each in after.items() if not each["is_available"]] == ["database"]


@pytest.mark.requirement("WF-ADM-0130-A")
def test_the_screen_gives_the_installed_version_and_the_date_of_the_latest_reading_of_the_accounts(
    contract: OpenAPI,
    platform: Services,
    database: Database,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'écran indique la version installée et la date de la dernière lecture des comptes du
    # fournisseur d'identité. » : the latest reading ended, read from the database, with its result.
    collected(prometheus)
    ended_task(database, "identity_sync", datetime(2026, 6, 2, 2, tzinfo=UTC), succeeded=False)
    ended_task(database, "identity_sync", datetime(2026, 6, 3, 2, tzinfo=UTC), succeeded=True)
    status = read(screen_on(contract, platform, prometheus), viewer)
    assert status["version"] == __version__
    assert status["last_identity_sync"] == {
        "at": "2026-06-03T02:00:00Z",
        "succeeded": True,
        "problem": None,
    }


@pytest.mark.requirement("WF-ADM-0130-A")
def test_the_screen_presents_the_cache_validity_in_force(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'écran présente la durée de validité du cache en vigueur. » : the value the settings give,
    # not the shipped one; the six others beside it, and the avatar of the installation.
    parameters = OperatingParameters(
        cache_validity_seconds=30, storage_usage_threshold=Decimal("0.9")
    )
    status = read(screen_on(contract, platform, prometheus, parameters), viewer)
    assert status["operating_parameters"] == {
        "cache_validity_seconds": 30,
        "background_task_retention_days": 30,
        "avatar_max_bytes": 512 * 1024,
        "task_queue_age_threshold_seconds": 900,
        "storage_usage_threshold": "0.9",
        "error_rate_threshold": "0.05",
        "error_rate_window_seconds": 300,
    }


@pytest.mark.requirement("WF-EXP-0030-A")
def test_the_screen_shows_the_same_version_for_the_three_processes(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'écran d'état affiche la même version pour les trois processus. » : the installed version,
    # which the front, the API and the worker share, and the one the API and the worker announce.
    collected(prometheus)
    status = read(screen_on(contract, platform, prometheus), viewer)
    components = by_component(status)
    assert status["version"] == components["api"]["version"] == components["worker"]["version"]
    assert status["version"] == __version__


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_screen_presents_the_version_of_each_component(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'écran d'état présente la version de chaque composant. » : the one each announces in the
    # metrics, Prometheus's its own; the object storage announces none, as the contract says.
    collected(prometheus)
    components = by_component(read(screen_on(contract, platform, prometheus), viewer))
    assert {c: each["version"] for c, each in components.items()} == {
        **VERSIONS_SAID,
        "object_storage": None,
        "identity_provider": None,
        "metrics": "3.16.0",
    }


@pytest.mark.story("US-2890")
def test_two_versions_announced_while_an_update_replaces_the_instances_are_both_said(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # Proper to US-2890: an instance of each version answers; the screen hides neither.
    collected(prometheus)
    announced = [({"component": "api", "version": v}, 1.0) for v in ("1.1.0", "1.0.0")]
    prometheus.holds(VERSIONS, announced)
    components = by_component(read(screen_on(contract, platform, prometheus), viewer))
    assert components["api"]["version"] == "1.0.0, 1.1.0"


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_component_stopped_a_scheduled_backup_failed_and_a_storage_full_each_show_an_alert(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'arrêt d'un composant, l'échec d'une sauvegarde planifiée et la saturation du stockage
    # produisent chacun une alerte visible sur l'écran d'état. » : each alert Prometheus holds in
    # progress, with the date it appeared, the latest first; the storage with its space then.
    collected(prometheus)
    full = datetime(2026, 6, 3, 11, 20, tzinfo=UTC)
    prometheus.holds(USED, [({"component": "database"}, 205.0 * GIB)], full)
    prometheus.holds(AVAILABLE, [({"component": "database"}, 9.0 * GIB)], full)
    stopped = datetime(2026, 6, 3, 0, 52, tzinfo=UTC)
    failed = datetime(2026, 6, 3, 1, tzinfo=UTC)
    prometheus.fires("component_unavailable", stopped, component="object_storage", severity="alert")
    prometheus.fires("scheduled_backup_failed", failed, severity="alert")
    prometheus.fires("storage_nearly_full", full, component="database", severity="watch")
    status = read(screen_on(contract, platform, prometheus), viewer)
    assert status["alerts"] == [
        {
            "code": "storage_nearly_full",
            "since": "2026-06-03T11:20:00Z",
            "severity": "watch",
            "params": {"used_bytes": 205 * GIB, "available_bytes": 9 * GIB},
        },
        {"code": "scheduled_backup_failed", "since": "2026-06-03T01:00:00Z", "severity": "alert"},
        {
            "code": "component_unavailable",
            "since": "2026-06-03T00:52:00Z",
            "severity": "alert",
            "params": {"component": "object_storage"},
        },
    ]


@pytest.mark.requirement("WF-OBS-0030-A")
def test_an_alert_disappears_from_the_screen_as_soon_as_its_cause_has_ceased(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « Une alerte disparaît de l'écran dès que sa cause a cessé. » : the rule no longer true, the
    # alert is no longer in progress in Prometheus, and the next reading of the screen has none.
    collected(prometheus)
    prometheus.fires("task_queue_stalled", CHECKED_AT, severity="alert")
    screen = screen_on(contract, platform, prometheus)
    assert [each["code"] for each in read(screen, viewer)["alerts"]] == ["task_queue_stalled"]
    prometheus.alerts.clear()
    assert read(screen, viewer)["alerts"] == []


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_worker_stopped_the_queue_that_ages_is_seen_on_the_screen(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # « L'arrêt du worker fait croître l'âge de la plus ancienne tâche en file, et cette croissance
    # est visible sur l'écran d'état. » : the screen presents the age by its threshold, the alert of
    # the queue, which the rule raises on the metric of the age, and the worker unavailable.
    collected(prometheus, down=("worker",))
    prometheus.fires("task_queue_stalled", CHECKED_AT, severity="alert")
    status = read(screen_on(contract, platform, prometheus), viewer)
    assert by_component(status)["worker"]["is_available"] is False
    assert [each["code"] for each in status["alerts"]] == ["task_queue_stalled"]


@pytest.mark.story("US-2880")
def test_prometheus_unavailable_the_screen_says_so_and_presents_none_of_the_metrics(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    database: Database,
    viewer: dict[str, str],
) -> None:
    # Proper to US-2880: « Prometheus indisponible, l'écran d'état le dit » : the component metrics
    # unavailable, alone; what the database holds is still said (§4.5.4, table 12).
    collected(prometheus)
    prometheus.fires("task_queue_stalled", CHECKED_AT, severity="alert")
    ended_task(database, "backup", datetime(2026, 6, 3, 1, tzinfo=UTC), succeeded=True)
    screen = screen_on(contract, platform, prometheus)
    prometheus.stop()
    status = read(screen, viewer)
    assert [(each["component"], each["is_available"]) for each in status["components"]] == [
        ("metrics", False)
    ]
    assert (status["alerts"], status["storage"]) == ([], UNMEASURED)
    assert status["last_backup"] == {
        "at": "2026-06-03T01:00:00Z",
        "succeeded": True,
        "problem": None,
    }


@pytest.mark.story("US-2880")
@pytest.mark.parametrize("fault", ["status", "garbled", "unconfigured"])
def test_a_prometheus_that_answers_wrong_or_is_not_given_is_said_unavailable(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
    fault: str,
) -> None:
    # Proper to US-2880: an answer that is not the query API's, or no address of Prometheus, is
    # Prometheus unavailable on the screen, never a failure of the screen.
    collected(prometheus)
    prometheus.status = 503 if fault == "status" else 200
    prometheus.garbled = fault == "garbled"
    served = None if fault == "unconfigured" else prometheus
    status = read(screen_on(contract, platform, served), viewer)
    assert [(each["component"], each["is_available"]) for each in status["components"]] == [
        ("metrics", False)
    ]


@pytest.mark.story("US-2880")
def test_the_api_reads_the_metrics_and_the_alerts_by_the_query_api_of_prometheus(
    prometheus: TestPrometheus,
) -> None:
    # Proper to US-2880: « l'API lit les métriques et les alertes en cours par l'API de requête de
    # Prometheus (TFX-14) » : the expressions it asks, the alerts and the build of Prometheus.
    collected(prometheus)
    client = Prometheus(prometheus.address)
    try:
        observation = client.observe()
    finally:
        client.close()
    assert {AVAILABILITY, CHECKED, VERSIONS, USED, AVAILABLE, "/api/v1/alerts"} <= set(
        prometheus.asked
    )
    assert observation.availabilities["cache"].version == "8.2.1"
    assert observation.version == "3.16.0"


@pytest.mark.story("US-2880")
def test_an_answer_of_prometheus_without_its_vector_is_a_failure_of_prometheus() -> None:
    # Proper to US-2880: an answer that says success without the shape of a vector is not read as
    # an empty platform.
    served = TestPrometheus()
    served.shapeless = True
    client = Prometheus(served.address)
    try:
        with pytest.raises(PrometheusError):
            client.query(USED)
    finally:
        client.close()
        served.stop()


@pytest.mark.story("US-2890")
def test_the_latest_backup_says_its_failure_by_the_problem_of_its_task(
    contract: OpenAPI,
    platform: Services,
    database: Database,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # Proper to US-2890: the dates and the results come from the database (WF-OBS-0010); a backup
    # failed says the problem of its task, with its correlation (WF-OBS-0020). The external copy and
    # the restore test are not kept yet: null.
    collected(prometheus)
    ended_task(database, "backup", datetime(2026, 6, 3, 1, tzinfo=UTC), succeeded=False)
    status = read(screen_on(contract, platform, prometheus), viewer)
    assert status["last_backup"] == {
        "at": "2026-06-03T01:00:00Z",
        "succeeded": False,
        "problem": {
            "code": "COMPONENT_UNAVAILABLE",
            "status": 503,
            "params": {"component": "object_storage"},
            "correlation_id": CORRELATION,
        },
    }
    assert status["last_identity_sync"] is None
    assert (status["last_backup_copy"], status["last_restore_test"]) == (None, None)


@pytest.mark.story("US-2890")
def test_the_screen_is_refused_without_the_permission_to_view_the_status(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    database: Database,
    realm: TestRealm,
) -> None:
    # Proper to US-2890: readable under ``system_status.read`` alone (WF-ADM-0100); without it, the
    # screen does not exist for the caller.
    answer = screen_on(contract, platform, prometheus).get(
        STATUS, headers=holding(database, realm, "users.read")
    )
    assert (answer.status_code, answer.json()["code"]) == (404, "NOT_FOUND")


def space(component: str, used: int, available: int | None) -> Space:
    return Space(component, used, available)


@pytest.mark.story("US-2890")
def test_the_storage_presented_is_the_space_whose_occupancy_is_the_highest() -> None:
    # Proper to US-2890 (#4128): of PostgreSQL and the object storage, the closer to saturation,
    # whichever is larger.
    database, storage = space("database", 80, 20), space("object_storage", 300, 700)
    assert fullest([storage, database]) == {"used_bytes": 80, "available_bytes": 20}
    assert fullest([space("database", 10, 90), storage]) == {
        "used_bytes": 300,
        "available_bytes": 700,
    }


@pytest.mark.story("US-2890")
def test_two_spaces_at_the_same_occupancy_present_the_object_storage() -> None:
    # Proper to US-2890: the contract does not say which; the rule gives the object storage, in
    # either order.
    database, storage = space("database", 50, 50), space("object_storage", 5, 5)
    assert (
        fullest([database, storage])
        == fullest([storage, database])
        == {
            "used_bytes": 5,
            "available_bytes": 5,
        }
    )


@pytest.mark.story("US-2890")
def test_a_space_without_its_capacity_is_not_presented_and_none_measured_says_nothing() -> None:
    # Proper to US-2890: a capacity not declared gives no rate (WF-OBS-0010): the space is not
    # compared; none measured, the screen says neither used nor left.
    assert fullest([space("database", 900, None), space("object_storage", 1, 9)]) == {
        "used_bytes": 1,
        "available_bytes": 9,
    }
    assert fullest([space("database", 900, None)]) == UNMEASURED
    assert fullest([space("database", 0, 0)]) == {"used_bytes": 0, "available_bytes": 0}


@pytest.mark.story("US-2890")
def test_an_alert_the_contract_does_not_name_is_not_presented() -> None:
    # Proper to US-2890: a rule an operator adds is Prometheus's, not the screen's; a zone the
    # contract does not have is read as an alert, and a component it does not name is not said.
    since = CHECKED_AT
    assert alert(FiringAlert("disk_on_fire", {"severity": "alert"}, since)) is None
    assert alert(FiringAlert("component_unavailable", {"component": "kafka"}, since)) == {
        "code": "component_unavailable",
        "since": since,
        "severity": "alert",
    }
    assert alert(FiringAlert("storage_nearly_full", {"severity": "watch"}, since)) == {
        "code": "storage_nearly_full",
        "since": since,
        "severity": "watch",
    }


@pytest.mark.story("US-2890")
def test_a_component_no_collection_has_found_is_not_said_available(
    contract: OpenAPI,
    platform: Services,
    prometheus: TestPrometheus,
    viewer: dict[str, str],
) -> None:
    # Proper to US-2890: a Prometheus that has collected nothing yet says nothing available, at the
    # date of the reading; itself available.
    components = by_component(read(screen_on(contract, platform, prometheus), viewer))
    assert [c for c, each in components.items() if each["is_available"]] == ["metrics"]
    assert components["database"]["version"] is None
