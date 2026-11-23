# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A workbook of a remaining to commit that lacks a column is refused at the opening (US-3200).

``openImport`` answers 422 ``FILE_FORMAT_UNREADABLE`` and names each column missing with its tab
(``params.missing_columns``): no remaining is set to zero, no task finished, no line created or
removed (#4421). A header renamed (« Débours restant (€) ») is a column absent.
"""

from typing import TYPE_CHECKING

import pytest
from estimate_support import Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import nodes, refusal
from missing_columns_support import lines_held, rewritten
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_import_support import Rows, labour, material, opening, workbook
from remaining_support import in_progress
from sqlalchemy import select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from nodes_support import Tree
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

OUTSIDE = "Hors sous-projet"
UNREADABLE = "FILE_FORMAT_UNREADABLE"


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
def scene(api: ContractClient, stage: Scene) -> Rows:
    """Give the project In progress, its tasks and their lines, as a workbook names them."""
    costs: Costing = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **labour(costs, "Raccordement", "2", "10"))
        lines.made(wiring, **material(costs, "Fournitures", "1", "100"))
        tests = tree.made("Essais")
        lines.made(tests, **material(costs, "Banc", "1", "50"))
        tree.made("Réception")
        tree.made("Clôture")

    return Rows(stage, in_progress(api, stage, build), costs)


def exported(scene: Rows) -> bytes:
    """Give the workbook of the lines, as the export writes it, their remaining set to zero."""
    rows = [
        scene.known("Câblage", "Raccordement", days=1),
        scene.known("Câblage", "Fournitures", amount=0),
        scene.known("Essais", "Banc", amount=0),
    ]
    return workbook({OUTSIDE: rows}, scene.tasks())


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.requirement("WF-INTF-0120-A")
@pytest.mark.parametrize(
    ("header", "new"),
    [
        pytest.param("ID ligne", None, id="without-lineage"),
        pytest.param("Jours restants", None, id="without-days"),
        pytest.param("Débours restant", None, id="without-amount"),
        pytest.param("Débours restant", "Débours restant (€)", id="renamed"),
    ],
)
def test_a_remaining_whose_tab_lacks_a_column_is_refused_naming_it_and_changes_nothing(
    api: ContractClient, stage: Scene, scene: Rows, header: str, new: str | None
) -> None:
    # « un reste à engager dont un onglet n'a plus « ID ligne », « Jours restants » ou « Débours
    # restant » est refusé par openImport, 422 FILE_FORMAT_UNREADABLE […] params.missing_columns
    # nommant chaque colonne manquante avec son onglet » ; « Le projet est inchangé. » : aucun reste
    # n'est mis à zéro (les cellules du fichier portent zéro), aucune ligne créée ni retirée.
    content = rewritten(exported(scene), OUTSIDE, header, new)
    before = (nodes(stage.database), lines_held(stage.database))

    response = opening(api, stage, content)

    assert refusal(response) == (
        422,
        UNREADABLE,
        {
            "expected_format": "remaining",
            "expected_version": "1",
            "missing_columns": [{"header": header, "sheet": OUTSIDE}],
        },
    )
    assert (nodes(stage.database), lines_held(stage.database)) == before
    with stage.database.transaction() as session:
        assert session.scalars(select(ImportReport)).all() == []


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_remaining_lacking_several_columns_names_each_in_the_order_of_the_format(
    api: ContractClient, stage: Scene, scene: Rows
) -> None:
    content = rewritten(exported(scene), OUTSIDE, "Débours restant")
    content = rewritten(content, OUTSIDE, "ID ligne")

    response = opening(api, stage, content)

    assert refusal(response)[2]["missing_columns"] == [
        {"header": "Débours restant", "sheet": OUTSIDE},
        {"header": "ID ligne", "sheet": OUTSIDE},
    ]


@pytest.mark.story("US-3200")
@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_remaining_with_its_columns_opens_and_a_cell_cleared_stays_for_the_analysis(
    api: ContractClient, stage: Scene, scene: Rows
) -> None:
    # « un classeur exporté, toutes ses colonnes lues présentes, s'ouvre comme avant » ; la règle
    # d'une cellule de reste effacée vaut pour une colonne présente, inchangée : le fichier s'ouvre.
    rows = [scene.known("Câblage", "Fournitures", amount=None)]
    response = opening(api, stage, workbook({OUTSIDE: rows}, scene.tasks()))

    assert response.status_code == 202, response.text
