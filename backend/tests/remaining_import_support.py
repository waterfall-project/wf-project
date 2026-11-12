# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the import of a remaining to commit share: its workbook, its rows, its steps.

Taken out of ``test_remaining_import.py`` (US-1630/L5) when it reached the size a file may have:
the workbook « Reste à engager » written as the export does, the rows of the project In progress
named as the import names them, and the steps — open, analyse, report, apply — through the service
and its worker. The fixtures stay in the test files, as everywhere in the suite.
"""

from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import UUID

from estimate_import_support import entry_of
from imports_trial import apply, deposited, read, run
from openpyxl import Workbook
from projects_support import PROJECTS, Scene
from remaining_support import Review, line_named, task_named
from sqlalchemy import select

from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.estimate.remaining.excel.layout import REVIEW_DATE_CELL
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Task
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from estimate_support import Costing
    from support import ContractClient

    from waterfall.worker.runner import Worker

HEADERS = [
    "Tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Jours restants",
    "Débours restant",
    "ID ligne",
]
REVIEW = utc_now().date()


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
