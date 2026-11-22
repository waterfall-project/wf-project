# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The latest test of a restoration on the status screen, dated, and one that did not take place.

The tests are inscribed as ``waterfall-restore test`` inscribes them (``record_restore_test``);
the screen reads the latest, and says a failure once it is older than a month: a test that could
not run — no backup to test, its Job never made, the production out of reach — inscribes nothing
(#4643). Before any test, the first is said missed a month after a backup could have been tested.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from backup_rows import Row, recorded
from fastapi.testclient import TestClient
from installed_reference import holding, install
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.status import RESTORE_TEST_FAILED, StatusSources
from waterfall.core.backups.interface import (
    RESTORE_TEST_PERIOD,
    BackupToTest,
    RestoreCounts,
    RestoreTestOutcome,
    RestoreTestResult,
    latest_restore_test,
    record_restore_test,
)
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import ServiceSettings

STATUS = "/api/v1/system/status"
COUNTS = RestoreCounts(projects=3, marked_revisions=12, cost_lines=40, identity_accounts=5)
NOW = datetime(2026, 7, 10, 12, tzinfo=UTC)


def inscribed(database: Database, finished_at: datetime, failure: str | None = None) -> None:
    """Inscribe a test ended at a moment, on a backup of the day before, failed if a reason."""
    backup = BackupToTest(uuid4(), finished_at - timedelta(days=1), "backups/tested.tar")
    started_at = finished_at - timedelta(minutes=40)
    outcome = RestoreTestOutcome(started_at, finished_at, backup, COUNTS, failure)
    with database.transaction() as session:
        record_restore_test(session, outcome)


def latest_at(database: Database, now: datetime) -> RestoreTestResult | None:
    with database.transaction() as session:
        return latest_restore_test(session, now)


@pytest.fixture
def platform(
    database: Database, keycloak: Keycloak, realm_settings: ServiceSettings, owner: Engine
) -> Services:
    install(owner)
    return Services(database, keycloak, KeycloakAdmin(keycloak, realm_settings), *nowhere())


def screen_read(contract: OpenAPI, platform: Services, viewer: dict[str, str]) -> dict[str, Any]:
    """Read the status screen, without Prometheus, as an account that is contributor to none."""
    app = create_app(platform, sources=StatusSources())
    screen = ContractClient(TestClient(app, raise_server_exceptions=False), contract)
    answer = screen.get(STATUS, headers=viewer)
    assert answer.status_code == 200, answer.text
    return answer.json()


@pytest.mark.requirement("WF-ADM-0130-A")
@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_screen_indicates_the_date_and_the_result_of_the_latest_restore_test(
    contract: OpenAPI, platform: Services, database: Database, realm: TestRealm
) -> None:
    # « L'écran indique la date du dernier test de restauration. » (WF-ADM-0130-A) ; « Un test de
    # restauration mensuel est exécuté, et son résultat daté est consultable. » (WF-EXP-0060-A) :
    # null while none has taken place, then the latest inscribed, its date and its result.
    viewer = holding(database, realm, "system_status.read")
    assert screen_read(contract, platform, viewer)["last_restore_test"] is None
    latest = (utc_now() - timedelta(days=2)).replace(microsecond=0)
    inscribed(database, latest - timedelta(days=30), "projects_differ")
    inscribed(database, latest)
    said = screen_read(contract, platform, viewer)["last_restore_test"]
    assert said == {
        "at": latest.isoformat().replace("+00:00", "Z"),
        "succeeded": True,
        "problem": None,
    }


@pytest.mark.requirement("WF-EXP-0060-A")
def test_a_failed_test_is_said_failed_on_the_screen(
    contract: OpenAPI, platform: Services, database: Database, realm: TestRealm
) -> None:
    # « Le test échoue et le signale si le nombre de projets restaurés diffère de celui de la
    # sauvegarde. » : the reason is in its row and its journal; the screen says the failure, by the
    # one code of the catalogue that names an unexpected failure.
    viewer = holding(database, realm, "system_status.read")
    latest = (utc_now() - timedelta(hours=3)).replace(microsecond=0)
    inscribed(database, latest, "projects_differ")
    said = screen_read(contract, platform, viewer)["last_restore_test"]
    assert said == {
        "at": latest.isoformat().replace("+00:00", "Z"),
        "succeeded": False,
        "problem": RESTORE_TEST_FAILED,
    }


@pytest.mark.story("US-2930")
def test_a_latest_test_older_than_a_month_says_the_test_that_was_due_missed(
    database: Database,
) -> None:
    # #4643: a test that does not take place inscribes nothing; the latest success ages, and once
    # older than the period it no longer says a success, but a failure at the end of the period.
    succeeded_at = NOW - RESTORE_TEST_PERIOD - timedelta(days=4)
    inscribed(database, succeeded_at)
    assert latest_at(database, NOW) == RestoreTestResult(
        succeeded_at + RESTORE_TEST_PERIOD, succeeded=False
    )
    just_before = succeeded_at + RESTORE_TEST_PERIOD - timedelta(seconds=1)
    assert latest_at(database, just_before) == RestoreTestResult(succeeded_at, succeeded=True)


@pytest.mark.story("US-2930")
def test_no_test_inscribed_is_none_and_the_latest_is_read_whatever_the_order_inscribed(
    database: Database,
) -> None:
    assert latest_at(database, NOW) is None
    inscribed(database, NOW - timedelta(days=1), "not_started")
    inscribed(database, NOW - timedelta(days=9))
    assert latest_at(database, NOW) == RestoreTestResult(NOW - timedelta(days=1), succeeded=False)


@pytest.mark.requirement("WF-EXP-0060-A")
def test_no_test_inscribed_a_month_after_the_first_backup_verified_says_the_first_test_missed(
    database: Database,
) -> None:
    # #4643: a Job that never starts — its image, a quota, a Role — inscribes nothing, even the
    # first time. The first test was due a period after the oldest scheduled backup verified: a
    # manual backup, or one whose verification failed, could not be tested, and does not count.
    recorded(database, NOW - timedelta(days=60), Row(origin="manual"))
    recorded(database, NOW - timedelta(days=50), Row(origin="scheduled", verification="failed"))
    oldest = NOW - timedelta(days=40)
    recorded(database, oldest, Row(origin="scheduled"))
    recorded(database, NOW - timedelta(days=1), Row(origin="scheduled"))
    assert latest_at(database, NOW) == RestoreTestResult(
        oldest + RESTORE_TEST_PERIOD, succeeded=False
    )


@pytest.mark.story("US-2930")
def test_no_test_inscribed_before_a_month_after_the_first_backup_verified_says_nothing(
    database: Database,
) -> None:
    recorded(database, NOW - timedelta(days=60), Row(origin="manual"))
    recorded(database, NOW - timedelta(days=10), Row(origin="scheduled"))
    assert latest_at(database, NOW) is None
