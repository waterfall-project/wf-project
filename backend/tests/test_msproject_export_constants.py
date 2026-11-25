# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The constants of a tiny installation exported at 1 at least, and imported back (US-3210b, #4826).

The installation bounds its constants above nought only; the schema writes them as integers, and
the reader refuses a constant of unit at nought (US-3180b). The export writes each at 1 at least:
the file of an installation at 0.4 days a month is read back without a refusal, and without a
calendar gap, since the import compares the constants of the file to those of the installation
as the export writes them (``carried``).
"""

from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from nodes_support import opened
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import update
from support import ContractClient
from test_msproject_export import exported, import_file, the_planning

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.planning.msproject import carried, read_project, written_constants
from waterfall.core.planning.scheduling import UnitConstants, decimal_of
from waterfall.core.resource_settings.tables import DurationUnit
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.marking import mark as marking
from waterfall.worker.runner import Timing as WorkerTiming
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

pytestmark = pytest.mark.requirement("WF-PLA-0160-A")

AT_ONCE = WorkerTiming(claim_after=0, block=0.01, redeposit_every=0)


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


def test_a_constant_below_half_a_unit_is_written_one_and_carried_so() -> None:
    # [US-3210b] #4826: a quarter of a minute a day and a week, 0.4 days a month, each rounded
    # to nought by the schema, are written 1 — what the import compares the file to as well.
    tiny = UnitConstants(Decimal("0.004"), Decimal("0.004"), Decimal("0.4"))
    assert written_constants(tiny) == (1, 1, 1)
    minute = decimal_of(Fraction(1, 60))
    assert carried(tiny) == UnitConstants(minute, minute, Decimal(1))
    usual = UnitConstants(Decimal(8), Decimal(40), Decimal("21.67"))
    assert written_constants(usual) == (480, 2400, 22)


def test_an_installation_at_four_tenths_of_a_day_a_month_exports_and_imports_back_unrefused(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3210b] #4826: the export writes « DaysPerMonth » at 1, which the reader accepts (a
    # constant of unit at nought is refused since US-3180b); reimported, the file presents
    # neither refusal nor rejection, nor any gap of constants or calendars, and applies.
    with stage.owner.begin() as connection:
        connection.execute(update(DurationUnit).values(days_per_month=Decimal("0.4")))
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    content = exported(api, stage, worker, revision["revision_id"])
    assert read_project(content).project.days_per_month == 1
    found = import_file(api, stage, worker, content, apply=False)
    report = found["report"]
    assert (report["refusals"], report["rejected"], report["differences"]) == ([], [], [])
    assert (report["unit_constants"], report["calendar_gap"]) == (None, None)
    import_file(api, stage, worker, content, apply=True)
