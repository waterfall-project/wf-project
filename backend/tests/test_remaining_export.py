# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The export of a remaining to commit, and its round trip.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1630/L4 writes its tests here ("Les tests du back"): ``requestExport`` of the kind
``remaining``, then ``getBackgroundTaskResult``, on a project In progress whose reference is marked
and whose current revision is open (``remaining_support``); the workbook read back by openpyxl, and
imported again through the service, its worker and its contract (``test_remaining_import``).
"""

from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from imports_trial import AT_ONCE, read
from nodes_support import set_progress
from openpyxl import load_workbook
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, task_named
from sqlalchemy import update
from support import ContractClient
from test_remaining_import import (
    OUTSIDE,
    REVIEW,
    Rows,
    analysed,
    applied,
    labour,
    material,
    report,
    row_of,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.estimate.tables import EstimateLine
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.marking import mark as marking
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from estimate_support import Lines
    from nodes_support import Tree
    from openapi_core import OpenAPI
    from openpyxl import Workbook
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

TASKS = "/api/v1/tasks"
SPREADSHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SUMMARY = "Synthèse"
FIXED = ("Synthèse", "Tâches", "Paramètres")
LINEAGE = "ID ligne"


@pytest.fixture
def export_services(
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
def api(contract: OpenAPI, export_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(export_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker that runs the imports, the markings and the exports, into the test's bucket."""
    queue.prepare()
    imports = ImportTasks(backups_bucket)
    handlers = {
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "revision_mark": marking,
        "export": ExportTask(backups_bucket),
    }
    return Worker(database, queue, handlers, "worker", AT_ONCE)


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress, its tasks and their lines (as ``test_remaining_import``)."""

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **labour(costs, "Raccordement", "2", "10"))
        lines.made(wiring, **material(costs, "Fournitures", "1", "100"))
        tests = tree.made("Essais")
        lines.made(tests, **material(costs, "Banc", "1", "50"))
        lines.made(tests, **material(costs, "Câbles", "0", "20"))
        acceptance = tree.made("Réception")
        lines.made(acceptance, **material(costs, "Procès-verbal", "1", "10"))
        tree.made("Clôture")

    return in_progress(api, stage, build)


@pytest.fixture
def scene(stage: Scene, review: Review, costs: Costing) -> Rows:
    """Give the project In progress as the rows of a workbook name it."""
    return Rows(stage, review, costs)


def download(
    api: ContractClient, stage: Scene, worker: Worker, revision_id: str, **body: Any
) -> Any:
    """Ask for the export of the remaining to commit of a revision, run it, download its file.

    The contract declares the file a binary string, and the validator of the answers refuses the
    bytes of a workbook as no string: the answer of the download is read by the client of the
    application itself, the request is validated.
    """
    headers = stage.manager.headers
    asked = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/exports",
        headers=headers,
        json={"kind": "remaining", "revision_id": revision_id, **body},
    )
    assert asked.status_code == 202, asked.text
    assert worker.step()
    answer = api.client.get(f"{TASKS}/{asked.json()['task_id']}/result", headers=headers)
    assert answer.status_code == 200, answer.text
    return answer


def exported(
    api: ContractClient, stage: Scene, worker: Worker, revision_id: str, **body: Any
) -> bytes:
    """Export the remaining to commit of a revision as the manager does; give the workbook."""
    return bytes(download(api, stage, worker, revision_id, **body).content)


def book_of(content: bytes) -> Workbook:
    """Read a workbook as Excel would show its formulas, not its values."""
    return load_workbook(BytesIO(content))


def lines_of(content: bytes, name: str) -> list[dict[str, Any]]:
    """Read the lines of a tab of lines by their headers: those that carry a lineage."""
    sheet = book_of(content)[name]
    rows = sheet.iter_rows(values_only=True)
    found: list[dict[str, Any]] = []
    headers: list[str] | None = None
    for row in rows:
        if headers is None:
            if "Tâche" in row and LINEAGE in row:
                headers = [str(each) for each in row]
            continue
        held = dict(zip(headers, row, strict=False))
        if held[LINEAGE]:
            found.append(held)
    return found


def clean(content: bytes, stage: Scene, worker: Worker, api: ContractClient) -> dict[str, Any]:
    """Import a workbook again unchanged and apply it; give its report, which is without change."""
    import_id = analysed(api, stage, worker, content)
    found = report(api, stage, import_id)
    assert (found["differences"], found["rejected"], found["refusals"]) == ([], [], [])
    assert (found["signals"], found["ignored"], found["completed_tasks"]) == ([], [], [])
    assert found["unchanged_count"] == found["read_count"]
    applied(api, stage, worker, import_id)
    return found


# --- The workbook exported ------------------------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_remaining_of_a_current_revision_is_exported_in_a_workbook_named_after_its_project(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « un reste à engager exporté […] : un export de la révision en cours […], de la structure
    # principale par défaut » : requestExport (kind remaining), then getBackgroundTaskResult; the
    # file is a workbook of the spreadsheet type, named after the code of the project and the
    # version of its revision — none for a revision in progress —, the review of the day of the
    # request, and the lines of the tasks not completed by their lineage.
    revision = scene.tree.revision
    answer = download(api, stage, worker, revision["revision_id"])
    assert answer.headers["content-type"].startswith(SPREADSHEET)
    assert answer.headers["content-disposition"].startswith(
        'attachment; filename="PRJ-1580-en-cours-reste-a-engager.xlsx"'
    )
    book = book_of(answer.content)
    assert book.sheetnames == [SUMMARY, OUTSIDE, "Tâches", "Paramètres"]
    summary = book[SUMMARY]
    assert [summary[cell].value for cell in ("A1", "B1", "A2", "B2")] == [
        "Format",
        "Reste à engager",
        "Version",
        1,
    ]
    assert summary["B9"].value == REVIEW.isoformat()
    lines = lines_of(answer.content, OUTSIDE)
    assert [(each["Tâche"], each[LINEAGE]) for each in lines] == [
        (row[0], row[5]) for row in scene.exported()
    ]
    assert [each["Jours restants"] for each in lines][:1] == [2.5]
    assert [each["Débours restant"] for each in lines][1:] == [100, 50, 0, 10]
    listed = list(book["Tâches"].iter_rows(min_row=5, values_only=True))
    assert [(each[0], each[1]) for each in listed if each[0]] == list(scene.tasks().items())


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_review_date_is_the_one_asked_and_the_tasks_completed_are_not_in_the_file(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « la date de la revue en B9 — review_date, le jour de la demande par défaut » ; « les lignes
    # des tâches non terminées » : the acceptance is completed, its line is not exported.
    acceptance = task_named(scene.tree, "Réception")["node_id"]
    set_progress(stage, acceptance, "completed", date(2026, 3, 1))
    content = exported(
        api, stage, worker, scene.tree.revision["revision_id"], review_date="2027-02-15"
    )
    assert book_of(content)[SUMMARY]["B9"].value == "2027-02-15"
    labels = [each["Désignation"] for each in lines_of(content, OUTSIDE)]
    assert labels == ["Raccordement", "Fournitures", "Banc", "Câbles"]
    entries = [row[0] for row in book_of(content)["Tâches"].iter_rows(min_row=5, values_only=True)]
    assert "3 Réception" not in entries


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_amounts_of_the_header_of_a_tab_are_those_of_the_indicators_of_the_revision(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « Les montants des en-têtes sont ceux que remaining_indicators et costs calculent pour la
    # révision exportée » : the budget of the reference and the actual costs of a subproject, those
    # of the lines of none (the cost imputed to the project alone included) in « Hors sous-projet ».
    project_id = stage.project["project_id"]
    made = api.post(
        f"{PROJECTS}/{project_id}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-1", "label": "Lot 1"},
    )
    assert made.status_code == 201, made.text
    supplies = line_named(scene.tree, "Fournitures")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(supplies["node_id"]))
            .values(subproject_id=UUID(made.json()["subproject_id"]))
        )
    load_import(
        stage, UUID(project_id), [cost("FA-1", "SP-1", "70.00"), cost("FA-2", None, "30.00")]
    )
    revision_id = scene.tree.revision["revision_id"]
    served = api.get(
        f"{PROJECTS}/{project_id}/remaining-indicators?revision_id={revision_id}",
        headers=stage.manager.headers,
    ).json()["by_subproject"]
    content = exported(api, stage, worker, revision_id)
    book = book_of(content)
    assert book.sheetnames == [SUMMARY, "SP-1", OUTSIDE, "Tâches", "Paramètres"]
    for name, key in (("SP-1", made.json()["subproject_id"]), (OUTSIDE, "unassigned")):
        balance = next(each for each in served if each["key"] == key)
        sheet = book[name]
        assert Decimal(str(sheet["B4"].value)) == Decimal(balance["budget"]), name
        assert Decimal(str(sheet["B5"].value)) == Decimal(balance["actual_cost"]), name
    assert [each["Désignation"] for each in lines_of(content, "SP-1")] == ["Fournitures"]
    assert Decimal(str(book["SP-1"]["B5"].value)) == Decimal("70.00")
    assert Decimal(str(book[OUTSIDE]["B5"].value)) == Decimal("30.00")


# --- The command of the revision, the project that ended ------------------------------------------


@pytest.mark.requirement("WF-CYC-0110-A")
def test_the_remaining_is_exported_from_a_project_that_ended_and_from_a_marked_revision(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows, review: Review
) -> None:
    # « les exports restent » : the command ``export_remaining`` lacks no condition on a project
    # In progress, and remains on a terminal one, where the other commands are gone; the reference
    # (marked) is exported too, on its images.
    address = (
        f"{PROJECTS}/{stage.project['project_id']}/revisions/{scene.tree.revision['revision_id']}"
    )

    def exports() -> dict[str, list[str]]:
        listed = api.get(address, headers=stage.manager.headers).json()["available_commands"]
        return {
            each["command"]: each["missing_conditions"]
            for each in listed
            if each["command"].startswith("export_")
        }

    assert exports()["export_remaining"] == []
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    assert exports() == {
        "export_planning": [],
        "export_estimate": [],
        "export_remaining": [],
        "export_task_tree_image": [],
    }
    for revision in (scene.tree.revision, review.reference):
        content = exported(api, stage, worker, revision["revision_id"])
        assert len(lines_of(content, OUTSIDE)) == 5
    named = download(api, stage, worker, review.reference["revision_id"])
    assert named.headers["content-disposition"].startswith(
        'attachment; filename="PRJ-1580-v1.0-reste-a-engager.xlsx"'
    )


# --- The round trip -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_remaining_exported_then_imported_again_presents_no_difference_and_changes_no_line(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « Même critère d'aller-retour que WF-INTF-0110. » : exported then imported again in the
    # current revision without a change, the report holds no difference and no rejection,
    # ``unchanged_count`` is ``read_count``, and the lines read again are identical.
    before = scene.tree.items()
    content = exported(api, stage, worker, scene.tree.revision["revision_id"])
    found = clean(content, stage, worker, api)
    assert found["read_count"] == 5
    assert scene.tree.items() == before
    marks = [row_of(stage, line_named(scene.tree, label)["node_id"]) for label in ("Banc",)]
    assert [each.reestimated_at for each in marks] == [None]


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_remaining_exported_from_a_marked_revision_is_imported_in_the_current_one_creating_none(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows, review: Review
) -> None:
    # « un export de la révision en cours ou d'une révision marquée » ; « Un reste à engager
    # exporté d'une révision marquée puis réimporté dans la révision en cours met à jour les
    # lignes de même lignée sans en créer aucune. » : the reference is marked, exported, and
    # imported in the current revision, which shares its lineages; no line is created and no
    # revision opened.
    before = scene.tree.items()
    content = exported(api, stage, worker, review.reference["revision_id"])
    import_id = analysed(api, stage, worker, content)
    found = report(api, stage, import_id)
    assert all(each["change"] != "added" for each in found["differences"])
    assert (found["differences"], found["rejected"]) == ([], [])
    assert found["unchanged_count"] == found["read_count"] == 5
    applied(api, stage, worker, import_id)
    assert scene.tree.items() == before
    listed = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/revisions", headers=stage.manager.headers
    ).json()
    assert len(listed["items"]) == 2
    assert read(api, stage, import_id)["status"] == "applied"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_two_subprojects_whose_codes_differ_in_case_only_are_exported_and_read_under_distinct_tabs(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # The export names its tabs as the import reads them (``tab_names``): ``SP-A`` and ``SP-a``
    # differ in their case only, which a workbook does not tell, so the second, in the order of the
    # codes, takes ``SP-a (2)``; a workbook imported again unchanged moves no line from one
    # subproject to the other.
    project_id = stage.project["project_id"]
    subprojects: dict[str, str] = {}
    for code in ("SP-A", "SP-a"):
        made = api.post(
            f"{PROJECTS}/{project_id}/subprojects",
            headers=stage.manager.headers,
            json={"code": code, "label": f"Lot {code}"},
        )
        assert made.status_code == 201, made.text
        subprojects[code] = made.json()["subproject_id"]
    placed = {"Fournitures": "SP-A", "Banc": "SP-a"}
    with stage.owner.begin() as connection:
        for label, code in placed.items():
            connection.execute(
                update(EstimateLine)
                .where(EstimateLine.node_id == UUID(line_named(scene.tree, label)["node_id"]))
                .values(subproject_id=UUID(subprojects[code]))
            )
    content = exported(api, stage, worker, scene.tree.revision["revision_id"])
    assert book_of(content).sheetnames == [
        SUMMARY,
        "SP-A",
        "SP-a (2)",
        OUTSIDE,
        "Tâches",
        "Paramètres",
    ]
    assert [each["Désignation"] for each in lines_of(content, "SP-A")] == ["Fournitures"]
    assert [each["Désignation"] for each in lines_of(content, "SP-a (2)")] == ["Banc"]
    clean(content, stage, worker, api)
    for label, code in placed.items():
        node = line_named(scene.tree, label)["node_id"]
        assert row_of(stage, node).subproject_id == UUID(subprojects[code])
