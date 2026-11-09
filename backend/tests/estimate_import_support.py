# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the import of the workbook of an estimate share (US-1550/L3).

The workbook written as the export writes it, its rows, its import opened and analysed as the
manager does, the structure of two tasks the tests import into, the project read.
"""

from io import BytesIO
from typing import TYPE_CHECKING, Any

from estimate_support import Costing, Lines
from imports_trial import deposited, read, run, stored
from openpyxl import Workbook
from projects_support import PROJECTS, Scene
from sqlalchemy import select

from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.resource_settings.tables import ResourceRole

if TYPE_CHECKING:
    from uuid import UUID

    from nodes_support import Tree
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.worker.runner import Worker


HEADERS = [
    "Tâche",
    "Description de la tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Quantité",
    "Heures",
    "Débours unitaire",
    "Délai de paiement (j)",
    "Sous-projet",
    "Montant Waterfall",
    "ID ligne",
]
SHEET = "1 Études"
STATE = "STATE_FORBIDS_OPERATION"


def entry_of(database: Database, model: type[ResourceRole | CostCategory], key: UUID) -> str:
    """Give the entry « label (code) » the list of « Paramètres » shows of a role or a category."""
    with database.transaction() as session:
        label, code = session.execute(select(model.label, model.code).where(model.id == key)).one()
    return f"{label} ({code})"


def workbook(
    rows: list[list[Any]],
    tasks: dict[str, str] | None = None,
    header: tuple[Any, ...] = ("Format", "Devis", "Version", 1),
    sheet: list[Any] | None = None,
    notes: list[list[Any]] | None = None,
) -> bytes:
    """Write a workbook of the format: its header, « Tâches », a tab of lines, maybe notes."""
    book = Workbook()
    first = book.active
    assert first is not None
    first.title = "Présentation"
    first.append(list(header[:2]))
    first.append(list(header[2:]))
    listed = book.create_sheet("Tâches")
    listed.append(["Tâches de la structure"])
    listed.append(["Entrée", "ID tâche", "N°", "Libellé"])
    for entry, lineage in (tasks or {}).items():
        listed.append([entry, lineage, entry.split(" ")[0], entry])
    lines = book.create_sheet(SHEET)
    lines.append(sheet or HEADERS)
    for row in rows:
        lines.append(row)
    if notes is not None:
        written = book.create_sheet("Notes")
        for each in notes:
            written.append(each)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def row(task: str | None, entry: str | None, cells: dict[str, Any] | None = None) -> list[Any]:
    """Give a row of a tab of lines, by the headers of ``HEADERS``."""
    named = {"Tâche": task, "Rôle ou catégorie": entry, **(cells or {})}
    return [named.get(header) for header in HEADERS]


def opening(api: ContractClient, stage: Scene, content: bytes) -> Any:
    """Deposit a workbook and open its import as the manager does; give the answer."""
    upload_id = deposited(api, stage.manager, content)
    return api.post(
        f"{PROJECTS}/{stage.project['project_id']}/imports",
        headers=stage.manager.headers,
        json={"kind": "estimate", "upload_id": upload_id},
    )


def analysed_import(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> str:
    """Open the import of a workbook and run its analysis; give the import."""
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    return response.json()["import_id"]


def analysed(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, *, kept: bool = False
) -> dict[str, Any]:
    """Open the import of a workbook, run its analysis; give its report, read by ``getImport``.

    ``kept`` reads it as the database keeps it.
    """
    import_id = analysed_import(api, stage, worker, content)
    if kept:
        row = stored(stage.database, import_id)
        assert row.status == "analysed"
        return dict(row.report or {})
    found = read(api, stage, import_id)
    assert found["status"] == "analysed", found
    return found["report"]


def by_lineage(tree: Tree) -> dict[str, dict[str, Any]]:
    """Give the nodes of the structure by their lineage."""
    return {item["lineage_id"]: item for item in tree.items()}


def two_tasks(tree: Tree, costs: Costing, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first.

    ``tree`` and ``costs`` are the structure and the categories it is written with.
    """
    first, second = tree.made("Câblage"), tree.made("Essais")
    lines = Lines(tree)
    labour = lines.made(first, quantity="2", resource_role_id=str(costs.role), hours="10")
    stuff = lines.made(
        first, quantity="1", cost_category_id=str(costs.material), unit_disbursement="350.00"
    )
    return {
        "first": first,
        "second": second,
        "labour": labour["nodes"][0],
        "material": stuff["nodes"][0],
        "role": entry_of(stage.database, ResourceRole, costs.role),
        "stuff": entry_of(stage.database, CostCategory, costs.material),
        "tasks": {"1 Câblage": first["lineage_id"], "2 Essais": second["lineage_id"]},
        "tree": tree,
        "costs": costs,
    }


def as_exported(held: dict[str, Any], changes: dict[str, Any] | None = None) -> list[list[Any]]:
    """Give the rows the export writes of the two lines of ``held``, the labour line changed."""
    labour, stuff = held["labour"], held["material"]
    return [
        row(
            "1 Câblage",
            held["role"],
            {
                "Désignation": labour["estimate_line"]["label"],
                "Quantité": 2,
                "Heures": 10,
                "Délai de paiement (j)": 0,
                "ID ligne": labour["lineage_id"],
                **(changes or {}),
            },
        ),
        row(
            "1 Câblage",
            held["stuff"],
            {
                "Désignation": stuff["estimate_line"]["label"],
                "Quantité": 1,
                "Débours unitaire": 350,
                "Délai de paiement (j)": 0,
                "ID ligne": stuff["lineage_id"],
            },
        ),
    ]


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage as its manager does."""
    answer = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()
