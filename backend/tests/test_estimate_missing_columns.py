# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A workbook of an estimate that lacks a column is refused at the opening (US-3200, #4421).

``openImport`` answers 422 ``FILE_FORMAT_UNREADABLE`` and names each column missing with its tab
(``params.missing_columns``, ``ProblemMissingColumn``); the project is unchanged and no import is
opened. A header renamed is a column absent.
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_import_support import HEADERS, SHEET, as_exported, opening, two_tasks, workbook
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from imports_trial import nodes, refusal
from missing_columns_support import lines_held, rewritten
from nodes_support import Tree, opened
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
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


@pytest.fixture
def held(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first."""
    costs: Costing = costing(stage.database)
    return two_tasks(Tree(api, stage, opened(api, stage)), costs, stage)


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize(
    ("header", "new"),
    [
        pytest.param("ID ligne", None, id="without-lineage"),
        pytest.param("Quantité", None, id="without-quantity"),
        pytest.param("Heures", None, id="without-hours"),
        pytest.param("Débours unitaire", None, id="without-unit-disbursement"),
        pytest.param("Débours unitaire", "Débours unitaire (€)", id="renamed"),
    ],
)
def test_a_workbook_whose_tab_lacks_a_column_read_is_refused_naming_it_and_changes_nothing(
    api: ContractClient, stage: Scene, held: dict[str, Any], header: str, new: str | None
) -> None:
    # « un devis dont un onglet de lignes n'a plus « ID ligne », « Quantité », « Heures » ou
    # « Débours unitaire » est refusé par openImport, 422 FILE_FORMAT_UNREADABLE, le format et la
    # version attendus nommés, et params.missing_columns nommant chaque colonne manquante avec son
    # onglet » ; « Le projet est inchangé. » : aucune ligne n'est créée ni retirée.
    content = rewritten(workbook(as_exported(held), held["tasks"]), SHEET, header, new)
    before = (nodes(stage.database), lines_held(stage.database))

    response = opening(api, stage, content)

    assert refusal(response) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {
            "expected_format": "estimate",
            "expected_version": "1",
            "missing_columns": [{"header": header, "sheet": SHEET}],
        },
    )
    assert (nodes(stage.database), lines_held(stage.database)) == before
    with stage.database.transaction() as session:
        assert session.scalars(select(ImportReport)).all() == []


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_workbook_without_the_lineage_neither_doubles_its_lines_nor_removes_those_it_replaces(
    api: ContractClient, stage: Scene, held: dict[str, Any]
) -> None:
    # Where the analysis took each line for new and those of the structure for absent (#4421), the
    # file is refused: the structure keeps its two lines, and the refusal names the tab.
    rows = [each[:-1] for each in as_exported(held)]
    content = workbook(rows, held["tasks"], sheet=HEADERS[:-1])
    before = lines_held(stage.database)

    response = opening(api, stage, content)

    assert refusal(response)[2]["missing_columns"] == [{"header": "ID ligne", "sheet": SHEET}]
    assert lines_held(stage.database) == before
    assert len(before) == 2


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_workbook_as_exported_opens_and_a_column_the_format_can_do_without_may_be_missing(
    api: ContractClient, stage: Scene, held: dict[str, Any]
) -> None:
    # « un classeur exporté, toutes ses colonnes lues présentes, s'ouvre comme avant ; une colonne
    # que le format ne lit pas peut manquer. »
    exported = opening(api, stage, workbook(as_exported(held), held["tasks"]))
    assert exported.status_code == 202, exported.text
    kept = [
        each for each in HEADERS if each not in {"Description de la tâche", "Montant Waterfall"}
    ]
    positions = [HEADERS.index(each) for each in kept]
    rows = [[row[at] for at in positions] for row in as_exported(held)]
    lean = opening(api, stage, workbook(rows, held["tasks"], sheet=kept))
    assert lean.status_code == 202, lean.text
