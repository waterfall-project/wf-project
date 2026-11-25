# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A workbook beyond the bounds is refused by ``openImport``, for the three formats Excel.

US-3190/L1, and L1b.

Through the service, each answer checked against the contract: the workbook of #4419 — a member
that inflates to 64 MiB in some 68 kB —, an archive whose member announces 1 GiB, and the workbook
of #4734 — a row of 2 000 000 empty cells in some 13 kB, which openpyxl took 583 MiB to read —,
deposited then opened by the manager of the project. The opening refuses them by the refusal of
the format, without openpyxl opening them and without the memory of the process rising; the
project is unchanged, no import is opened nor task deposited, and the deposit stays usable. The
readers themselves are ``test_workbook_bounds``'s.
"""

from functools import cache
from typing import TYPE_CHECKING, Any

import pytest
from actual_costs_import_support import declare, extraction, in_progress, line
from estimate_import_support import workbook as estimate_workbook
from fastapi.testclient import TestClient
from imports_trial import deposited, nodes, open_import, refusal
from projects_support import Scene, put_in_state
from projects_support import scene as make_scene
from remaining_import_support import workbook as remaining_workbook
from sqlalchemy import func, select
from support import ContractClient
from workbook_bombs import CALM, Rows, announcing, appended, lying, measured

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.interface import workbooks
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from collections.abc import Callable

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

UNREADABLE = "FILE_FORMAT_UNREADABLE"
EXPECTED = {
    "estimate": {"expected_format": "estimate", "expected_version": "1"},
    "remaining": {"expected_format": "remaining", "expected_version": "1"},
    "actual_costs": {"expected_format": "actual_costs"},
}
BASES: dict[str, Callable[[], bytes]] = {
    "estimate": lambda: estimate_workbook([]),
    "remaining": lambda: remaining_workbook({"Hors sous-projet": []}),
    "actual_costs": lambda: extraction([line()]),
}
BOMBS: dict[str, Callable[[bytes], bytes]] = {
    "inflates-64-MiB": lying,
    "announces-1-GiB": announcing,
    # The first tab, whose header each format reads at the opening.
    "a-row-of-2-000-000-cells": lambda base: appended(
        base, "xl/worksheets/sheet1.xml", Rows(cells=2_000_000)
    ),
}


@cache
def _bomb(kind: str, bomb: str) -> bytes:
    return BOMBS[bomb](BASES[kind]())


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
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def _ready(stage: Scene, kind: str) -> None:
    """Put the project where an import of ``kind`` reaches the reading of its header."""
    if kind == "remaining":
        put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    elif kind == "actual_costs":
        in_progress(stage)
        declare(stage.database)


def _held(database: Database) -> tuple[int, int]:
    """Count the imports and the tasks of the platform."""
    with database.transaction() as session:
        imports = session.scalar(select(func.count()).select_from(ImportReport))
        tasks = session.scalar(select(func.count()).select_from(BackgroundTask))
    return imports or 0, tasks or 0


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("bomb", list(BOMBS))
@pytest.mark.parametrize("kind", list(EXPECTED))
def test_a_workbook_beyond_the_bounds_is_refused_at_the_opening_and_the_project_unchanged(
    api: ContractClient,
    stage: Scene,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    bomb: str,
) -> None:
    # « un classeur dont la somme des tailles décompressées […] passe la borne de la conception est
    # refusé par openImport, 422 FILE_FORMAT_UNREADABLE, le format attendu nommé, sans avoir été
    # ouvert par le lecteur de classeurs : éprouvé sur un classeur de 68 515 octets dont un membre
    # se décompresse en 64 Mio, et sur une archive dont un membre annonce 1 Gio, la mémoire du
    # processus ne montant pas » ; « un classeur de 13 705 octets dont une ligne porte 2 000 000 de
    # cellules vides est refusé sans que la mémoire du processus ne monte » (US-3190/L1b) — « Le
    # projet est inchangé. » : et rien n'est mis en file : aucun import n'est ouvert, le dépôt
    # reste utilisable.
    _ready(stage, kind)
    content = _bomb(kind, bomb)
    upload_id = deposited(api, stage.manager, content)
    before = (nodes(stage.database), _held(stage.database))

    def opened(*_: object, **__: object) -> None:
        msg = "the workbook was opened"
        raise AssertionError(msg)

    monkeypatch.setattr(workbooks, "load_workbook", opened)
    project_id = stage.project["project_id"]
    answers: list[Any] = []
    with measured() as peak:
        answers.append(open_import(api, stage.manager, project_id, upload_id, kind=kind))
    assert refusal(answers[0]) == (422, UNREADABLE, EXPECTED[kind])
    assert peak.allocated < CALM
    assert (nodes(stage.database), _held(stage.database)) == before
    again = open_import(api, stage.manager, project_id, upload_id, kind=kind)
    assert refusal(again) == refusal(answers[0])
