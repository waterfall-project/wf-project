# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a remaining to commit: its analysis and its application.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1630/L3 writes its tests here ("Les tests du back"): the workbook « Reste à engager » opened,
analysed and applied through the service and its worker, on a project In progress whose reference
is marked and whose current revision is open (``remaining_support``); each answer checked against
the contract. The export, and the round trip with it, are US-1630/L4's.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from estimate_import_support import entry_of, project_of
from estimate_support import YEAR, Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import apply, deposited, import_worker, read, refusal, run, stored
from nodes_support import Tree, set_progress
from openpyxl import Workbook
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked, task_named
from sqlalchemy import select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.interface import set_hourly_rate
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.estimate.remaining.analysing import same_cell, tab_subprojects
from waterfall.core.estimate.remaining.excel.layout import REVIEW_DATE_CELL
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.platform.audit import Act
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

HEADERS = [
    "Tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Jours restants",
    "Débours restant",
    "ID ligne",
]
OUTSIDE = "Hors sous-projet"
STATE = "STATE_FORBIDS_OPERATION"
REVIEW = utc_now().date()
STARTED_ON = date(YEAR, 1, 1)
NEXT = YEAR + 1
LATER = datetime(NEXT, 1, 12, 10, tzinfo=UTC)


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
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress, its tasks and their lines.

    The wiring: its connection, two engineers for ten hours each, and its supplies at 100; the
    tests: their bench at 50 and cables of no quantity at 20; the acceptance, its report at 10;
    the closing, without a line.
    """

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


def labour(costs: Costing, label: str, quantity: str, hours: str) -> dict[str, Any]:
    """Give a labour line of the role of the scene."""
    return {
        "label": label,
        "quantity": quantity,
        "resource_role_id": str(costs.role),
        "hours": hours,
    }


def material(costs: Costing, label: str, quantity: str, amount: str) -> dict[str, Any]:
    """Give a line of material at the unit disbursement said."""
    return {
        "label": label,
        "quantity": quantity,
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def workbook(
    tabs: dict[str, list[list[Any]]],
    tasks: dict[str, str] | None = None,
    review: Any = REVIEW,
    version: Any = 1,
) -> bytes:
    """Write a workbook of the format: « Synthèse », its review in B9, « Tâches », the tabs."""
    book = Workbook()
    summary = book.active
    assert summary is not None
    summary.title = "Synthèse"
    summary.append(["Format", "Reste à engager"])
    summary.append(["Version", version])
    summary[REVIEW_DATE_CELL] = review
    listed = book.create_sheet("Tâches")
    listed.append(["Entrée", "ID tâche"])
    for entry, lineage in (tasks or {}).items():
        listed.append([entry, lineage])
    for name, rows in tabs.items():
        sheet = book.create_sheet(name)
        sheet.append(HEADERS)
        for row in rows:
            sheet.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


class Rows:
    """The project In progress of a test, read as the import names it: its tasks, its lines."""

    def __init__(self, stage: Scene, review: Review, costs: Costing) -> None:
        self.stage, self.tree, self.costs = stage, review.tree, costs
        self.role = entry_of(stage.database, ResourceRole, costs.role)
        self.stuff = entry_of(stage.database, CostCategory, costs.material)
        self.numbers = {"Câblage": "1", "Essais": "2", "Réception": "3", "Clôture": "4"}

    def tasks(self) -> dict[str, str]:
        """Give the entries of « Tâches »: each task by its number and label, its lineage."""
        return {
            f"{number} {label}": task_named(self.tree, label)["lineage_id"]
            for label, number in self.numbers.items()
        }

    def task(self, label: str) -> str:
        """Give the entry of a task in « Tâches »."""
        return f"{self.numbers[label]} {label}"

    def known(self, task: str, label: str, *, days: Any = None, amount: Any = None) -> list[Any]:
        """Give the row of a line the structure holds: task, entry, cells, lineage."""
        line = line_named(self.tree, label)
        entry = self.stuff if days is None else self.role
        return [self.task(task), entry, label, days, amount, line["lineage_id"]]

    def exported(self) -> list[list[Any]]:
        """Give the rows the export writes of the lines: 2.5 days, then the amounts left."""
        return [
            self.known("Câblage", "Raccordement", days=2.5),
            self.known("Câblage", "Fournitures", amount=100),
            self.known("Essais", "Banc", amount=50),
            self.known("Essais", "Câbles", amount=0),
            self.known("Réception", "Procès-verbal", amount=10),
        ]


@pytest.fixture
def scene(stage: Scene, review: Review, costs: Costing) -> Rows:
    """Give the project In progress as the rows of a workbook name it."""
    return Rows(stage, review, costs)


def opening(api: ContractClient, stage: Scene, content: bytes) -> Any:
    """Deposit a workbook and open its import as the manager does; give the answer."""
    upload_id = deposited(api, stage.manager, content)
    return api.post(
        f"{PROJECTS}/{stage.project['project_id']}/imports",
        headers=stage.manager.headers,
        json={"kind": "remaining", "upload_id": upload_id},
    )


def analysed(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> str:
    """Open the import of a workbook and run its analysis; give the import analysed."""
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    import_id = response.json()["import_id"]
    assert read(api, stage, import_id)["status"] == "analysed"
    return import_id


def report(api: ContractClient, stage: Scene, import_id: str) -> dict[str, Any]:
    """Read the report of an import."""
    return read(api, stage, import_id)["report"]


def applied(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> None:
    """Confirm the application of an import analysed and run it; it is applied."""
    answer = apply(api, stage, import_id)
    assert answer.status_code == 202, answer.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


def row_of(stage: Scene, node_id: str) -> EstimateLine:
    """Read a line of estimate as the base keeps it."""
    with stage.database.transaction() as session:
        row = session.get_one(EstimateLine, (UUID(stage.project["project_id"]), UUID(node_id)))
        session.expunge(row)
        return row


def task_row(stage: Scene, node_id: str) -> Task:
    """Read a task as the base keeps it."""
    with stage.database.transaction() as session:
        row = session.scalars(select(Task).where(Task.node_id == UUID(node_id))).one()
        session.expunge(row)
        return row


def codes(found: dict[str, Any]) -> list[tuple[int, str]]:
    """Give the rows a report rejects and their reasons."""
    return [(each["row"], each["code"]) for each in found["rejected"]]


# --- The cells compared, the tabs named -----------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_cell_is_the_one_exported_at_the_digits_a_spreadsheet_keeps() -> None:
    # The import computes again what the export wrote (2.5 days, or a third of a day written by a
    # float) and only a cell that differs from it is a change.
    third = Decimal(1) / Decimal(3)
    assert same_cell(Decimal(repr(float(third))), third)
    assert same_cell(Decimal(3), Decimal("3.000"))
    assert not same_cell(Decimal("2.5"), Decimal("2.6"))


@pytest.mark.requirement("WF-INTF-0120-A")
def test_the_tabs_are_named_by_the_codes_of_the_subprojects_as_the_writer_names_them() -> None:
    first, second = UUID(int=1), UUID(int=2)
    tabs = tab_subprojects({"SP/1": first, "sp-2": second})
    assert tabs == {"SP_1": first, "sp-2": second, "Hors sous-projet": None}


# --- The lines known, absent, created -------------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_remaining_reimported_updates_the_lines_of_its_lineage_and_creates_none(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « Un reste à engager exporté d'une révision marquée puis réimporté dans la révision en cours
    # met à jour les lignes de même lignée sans en créer aucune. » ; « Avec huit heures par jour,
    # une ligne de main-d'œuvre dont le fichier porte trois jours a un reste de vingt-quatre
    # heures. » ; « les montants budgétés et les lignées de toutes les lignes sont inchangés
    # après l'import, et une ligne absente du fichier conserve son reste à engager. » The rows of
    # the lines of the marked reference, the connection at three days, the bench absent.
    tree = scene.tree
    rows = [each for each in scene.exported() if each[2] != "Banc"]
    rows[0][3] = 3
    connection, bench = line_named(tree, "Raccordement"), line_named(tree, "Banc")
    before = row_of(stage, bench["node_id"])
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert found["differences"] == [
        {
            "change": "updated",
            "target": "estimate_line",
            "lineage_id": connection["lineage_id"],
            "label": "Raccordement",
            "fields": ["hours"],
        }
    ]
    assert (found["read_count"], found["unchanged_count"], found["rejected"]) == (4, 3, [])
    assert found["completed_tasks"] == []
    applied(api, stage, worker, import_id)
    written = row_of(stage, connection["node_id"])
    assert (written.quantity, written.hours) == (Decimal(2), Decimal(12))
    assert written.quantity * (written.hours or 0) == Decimal(24)
    assert written.budgeted_amount == Decimal(connection["estimate_line"]["budgeted_amount"])
    assert written.reestimated_at is not None
    assert line_named(tree, "Raccordement")["lineage_id"] == connection["lineage_id"]
    left = row_of(stage, bench["node_id"])
    assert (left.reestimated_amount, left.reestimated_at) == (before.reestimated_amount, None)
    assert row_of(stage, line_named(tree, "Fournitures")["node_id"]).reestimated_at is None


@pytest.mark.requirement("WF-INTF-0120-A")
def test_an_amount_left_is_written_as_a_unit_disbursement_the_quantity_kept_or_brought_to_one(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées » : the supplies at 150,
    # one unit; the cables, of no quantity, at 40: one unit of 40.
    rows = scene.exported()
    rows[1][4], rows[3][4] = 150, 40
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    fields = [each["fields"] for each in report(api, stage, import_id)["differences"]]
    assert fields == [["unit_disbursement"], ["quantity", "unit_disbursement"]]
    applied(api, stage, worker, import_id)
    supplies = row_of(stage, line_named(scene.tree, "Fournitures")["node_id"])
    cables = row_of(stage, line_named(scene.tree, "Câbles")["node_id"])
    assert (supplies.quantity, supplies.unit_disbursement) == (1, Decimal("150.00"))
    assert supplies.reestimated_amount == Decimal("150.00")
    assert (cables.quantity, cables.unit_disbursement) == (1, Decimal("40.00"))


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_line_without_a_lineage_is_created_at_a_budget_of_nought_under_the_task_it_names(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « une ligne sans identifiant créée à budgété nul sous la tâche qu'elle désigne, dans le
    # sous-projet de son onglet ; une ligne nouvelle sous une tâche terminée rejetée
    # (task_not_completed, params.tasks, #1794) ; une tâche […] inconnue […] rejetée comme au
    # devis ».
    closing = task_named(scene.tree, "Clôture")
    set_progress(stage, closing["node_id"], "completed", STARTED_ON)
    rows = [
        *scene.exported(),
        [scene.task("Essais"), scene.stuff, "Rallonge", None, 80, None],
        [scene.task("Clôture"), scene.stuff, "Archive", None, 5, None],
        ["Inconnue", scene.stuff, "Plan", None, 5, None],
    ]
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert [each["change"] for each in found["differences"]] == ["added"]
    assert codes(found) == [(8, STATE), (9, "UNKNOWN_TASK")]
    assert found["rejected"][0]["sheet"] == OUTSIDE
    assert found["rejected"][0]["params"] == {
        "missing_condition": "task_not_completed",
        "tasks": [{"lineage_id": closing["lineage_id"], "label": "Clôture"}],
    }
    assert found["rejected"][1]["params"] == {"value": "Inconnue"}
    applied(api, stage, worker, import_id)
    created = line_named(scene.tree, "Rallonge")
    row = row_of(stage, created["node_id"])
    assert (row.budgeted_amount, row.reestimated_amount) == (0, Decimal("80.00"))
    assert (row.subproject_id, row.reestimated_at is not None) == (None, True)
    assert created["parent_id"] == task_named(scene.tree, "Essais")["node_id"]


# --- The tasks completed at the date of the review ------------------------------------------------


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_task_whose_lines_the_file_sets_to_nought_is_completed_at_the_date_of_the_review(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « Une tâche démarrée dont toutes les lignes du fichier portent zéro est terminée à la date
    # de la revue ; une tâche non démarrée dont les lignes sont laissées telles quelles reste non
    # réestimée. » The wiring started, its two lines at nought; the tests, not started, their
    # bench at nought — their cables already are —; the acceptance left as it is.
    tree = scene.tree
    wiring, tests = task_named(tree, "Câblage"), task_named(tree, "Essais")
    set_progress(stage, wiring["node_id"], "started", STARTED_ON)
    rows = scene.exported()
    rows[0][3], rows[1][4], rows[2][4] = 0, 0, 0
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert found["completed_tasks"] == [
        {"lineage_id": wiring["lineage_id"], "label": "Câblage", "completed_on": str(REVIEW)},
        {"lineage_id": tests["lineage_id"], "label": "Essais", "completed_on": str(REVIEW)},
    ]
    applied(api, stage, worker, import_id)
    done = task_row(stage, wiring["node_id"])
    assert (done.progress, done.started_on, done.completed_on) == ("completed", STARTED_ON, REVIEW)
    done = task_row(stage, tests["node_id"])
    assert (done.progress, done.started_on, done.completed_on) == ("completed", REVIEW, REVIEW)
    left = task_row(stage, task_named(tree, "Réception")["node_id"])
    assert left.progress == "not_started"
    assert row_of(stage, line_named(tree, "Procès-verbal")["node_id"]).reestimated_at is None
    assert row_of(stage, line_named(tree, "Banc")["node_id"]).reestimated_at is not None


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_task_the_file_completes_without_a_date_of_review_rejects_its_lines_set_to_nought(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # The date of completion is the one « Synthèse » carries, never null: without it, the lines
    # that would complete their task are refused as their entry is (COMPLETION_DATE_REQUIRED).
    rows = scene.exported()
    rows[2][4] = 0
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks(), None))
    found = report(api, stage, import_id)
    assert codes(found) == [(4, "COMPLETION_DATE_REQUIRED")]
    assert (found["completed_tasks"], found["differences"]) == ([], [])


# --- The subproject of the tab --------------------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_line_placed_in_another_tab_changes_subproject_unless_it_received_actual_costs(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « une ligne d'une tâche démarrée dont le sous-projet a reçu des coûts réels, placée dans un
    # autre onglet, rejetée en nommant ce sous-projet (SUBPROJECT_HAS_ACTUAL_COSTS) ; une ligne
    # d'une tâche non démarrée placée dans un autre onglet en change, un écart subproject ».
    path = f"{PROJECTS}/{stage.project['project_id']}/subprojects"
    sent = {"code": "SP-1", "label": "Lot 1"}
    made = api.post(path, headers=stage.manager.headers, json=sent)
    assert made.status_code == 201, made.text
    subproject = made.json()["subproject_id"]
    supplies = line_named(scene.tree, "Fournitures")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(supplies["node_id"]))
            .values(subproject_id=UUID(subproject))
        )
    set_progress(stage, task_named(scene.tree, "Câblage")["node_id"], "started", STARTED_ON)
    load_import(stage, UUID(stage.project["project_id"]), [cost("FA-1", "SP-1")])
    rows = scene.exported()
    moved = rows.pop(2)
    import_id = analysed(api, stage, worker, workbook({"SP-1": [moved], OUTSIDE: rows}))
    found = report(api, stage, import_id)
    assert [(each["sheet"], each["row"], each["code"]) for each in found["rejected"]] == [
        (OUTSIDE, 3, "SUBPROJECT_HAS_ACTUAL_COSTS")
    ]
    named = found["rejected"][0]["params"]["subproject"]
    assert named == {"subproject_id": subproject, "label": "Lot 1"}
    [difference] = found["differences"]
    assert (difference["label"], difference["fields"]) == ("Banc", ["subproject"])
    applied(api, stage, worker, import_id)
    bench = row_of(stage, line_named(scene.tree, "Banc")["node_id"])
    assert (bench.subproject_id, bench.reestimated_at) == (UUID(subproject), None)


# --- The file refused, the phase ------------------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("version", [None, 2], ids=["without", "unknown"])
def test_a_remaining_without_a_version_or_of_an_unknown_one_is_refused_and_the_project_unchanged(
    api: ContractClient, stage: Scene, scene: Rows, version: Any
) -> None:
    # « Un fichier de devis ou de reste à engager sans version, ou d'une version non reconnue, est
    # refusé avec un message qui nomme le format et la version attendus » ; « Le projet est
    # inchangé. »
    before = scene.tree.items()
    answer = opening(api, stage, workbook({OUTSIDE: scene.exported()}, version=version))
    assert refusal(answer) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {"expected_format": "remaining", "expected_version": "1"},
    )
    assert scene.tree.items() == before


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_remaining_is_imported_on_a_project_in_progress_only(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # ``ProjectCommand.import_remaining`` lacks ``project_in_progress`` outside In progress: the
    # opening is refused, and the application of an import analysed before.
    content = workbook({OUTSIDE: scene.exported()}, scene.tasks())
    import_id = analysed(api, stage, worker, content)
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    answer = opening(api, stage, content)
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_in_progress"})
    assert refusal(apply(api, stage, import_id)) == refusal(answer)
    assert stored(stage.database, import_id).status == "refused"


# --- The revision an import creates -------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_remaining_imported_in_the_next_year_creates_a_revision_at_the_rates_projected(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    scene: Rows,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Une révision créée en 2027 par un import de reste à engager porte les taux de 2026
    # projetés d'une année ; la mise à jour catégorie par catégorie reste proposée jusqu'à son
    # marquage, et l'accepter pour une catégorie la rechiffre au taux de 2027. » Every revision
    # marked, the project inflating at 3 %, the engineering rated 70.00 for the next year.
    review_marked(stage, scene.tree.revision, "Revue 1")
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    with stage.database.transaction() as session:
        set_hourly_rate(
            session, (scene.costs.labour, NEXT), Decimal("70.00"), None, Act(None, LATER)
        )
    rows = scene.exported()
    rows[0][3] = 3
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    monkeypatch.setattr("waterfall.core.exchanges.running.utc_now", lambda: LATER)
    monkeypatch.setattr("waterfall.api.rate_update.utc_now", lambda: LATER)
    applied(api, stage, worker, import_id)
    created = project_of(api, stage)["current_revision_id"]
    assert created != scene.tree.revision["revision_id"]
    base = f"{PROJECTS}/{stage.project['project_id']}/revisions/{created}"
    revision = api.get(base, headers=stage.manager.headers).json()
    assert revision["reference_year"] == NEXT
    assert kept(stage, created) == {scene.costs.labour: (Decimal("66.95"), "projected")}
    proposed = api.get(f"{base}/rate-update", headers=stage.manager.headers).json()
    assert [each["cost_category_id"] for each in proposed["categories"]] == [
        str(scene.costs.labour)
    ]
    sent = {
        "cost_category_ids": [str(scene.costs.labour)],
        "lock_version": revision["lock_version"],
    }
    answer = api.post(f"{base}/rate-update", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    assert kept(stage, created) == {scene.costs.labour: (Decimal("70.00"), "reference")}
    with stage.database.transaction() as session:
        priced = session.execute(
            select(EstimateLine.quantity, EstimateLine.hours, EstimateLine.base_amount)
            .join(
                Node,
                (Node.project_id == EstimateLine.project_id) & (Node.id == EstimateLine.node_id),
            )
            .where(Node.revision_id == UUID(created), EstimateLine.resource_role_id.is_not(None))
        ).one()
    assert tuple(priced) == (Decimal(2), Decimal(12), Decimal("1680.00"))


def kept(stage: Scene, revision_id: str) -> dict[UUID, tuple[Decimal, str]]:
    """Read the rates a revision keeps, by category: their amount and their origin."""
    with stage.database.transaction() as session:
        rows = session.execute(
            select(RevisionRate.cost_category_id, RevisionRate.amount, RevisionRate.origin).where(
                RevisionRate.revision_id == UUID(revision_id)
            )
        ).all()
    return {row[0]: (row[1], row[2]) for row in rows}
