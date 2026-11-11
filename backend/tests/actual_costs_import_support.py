# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the import of an extraction of the actual costs share (US-1610).

The extraction written as the ERP gives it — its headers in row 1 of its first tab, a line per row
—, the mapping declared around the service, the project In progress under the code of the
examples of WF-CRE-0020, its subprojects, and its import opened and analysed as its manager does.
"""

from io import BytesIO
from typing import TYPE_CHECKING, Any

from imports_trial import deposited, read, run
from openpyxl import Workbook
from projects_support import PROJECTS, Scene, put_in_state
from sqlalchemy import select

from waterfall.core.cost_settings.interface import (
    ActualCostMappingWrite,
    ColumnLabels,
    read_actual_cost_mapping,
    replace_actual_cost_mapping,
)
from waterfall.core.costs.tables import CostLine
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.worker.runner import Worker

# The project of the examples of WF-CRE-0020: its code holds dots, its subproject is 10001.
CODE = "A.ABC.26001"
SUBPROJECT = "10001"
# The labels of the four required columns, as WF-REF-0190-A declares them, and of the item.
DECLARED = {
    "wbs_element": ["Elément d'OTP"],
    "document_number": ["Nº pièce référence"],
    "document_item": ["Poste"],
    "document_date": ["Date de la pièce"],
    "amount": ["Val./Devise objet"],
}
SOURCE_COLUMNS = ("wbs_element", "document_number", "document_item", "document_date", "amount")
# The headers of an extraction, as the ERP writes them: « Élément » accented, two columns besides.
HEADERS = (
    "Élément d'OTP",
    "Nº pièce référence",
    "Poste",
    "Date de la pièce",
    "Val./Devise objet",
    "Fournisseur",
    "Nom Matricule",
)
STATE = "STATE_FORBIDS_OPERATION"
UNREADABLE = "FILE_FORMAT_UNREADABLE"


def declare(
    database: Database,
    declared: Mapping[str, Sequence[str]] = DECLARED,
    kept: Iterable[str] = ("Fournisseur",),
) -> None:
    """Replace the mapping of the installation around the service: these labels, these kept."""
    with database.transaction() as session:
        version = read_actual_cost_mapping(session).lock_version
        columns = [
            ColumnLabels(column, list(declared.get(column, []))) for column in SOURCE_COLUMNS
        ]
        written = ActualCostMappingWrite(columns, list(kept))
        replace_actual_cost_mapping(session, written, version, Act(None, utc_now()))


def extraction(rows: Iterable[Sequence[Any]], headers: Sequence[Any] = HEADERS) -> bytes:
    """Write an extraction: its headers in row 1 of its first tab, a line per row, a tab besides."""
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "Extraction"
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    book.create_sheet("Notes").append(["Élément d'OTP", "ignoré"])
    out = BytesIO()
    book.save(out)
    return out.getvalue()


# A valid line of an extraction under ``HEADERS``, by the name of each cell.
VALID: dict[str, Any] = {
    "element": f"{CODE}/{SUBPROJECT}",
    "number": "5100001234",
    "item": None,
    "on": "2026-04-02",
    "amount": 1250,
    "supplier": "Atelier Durand",
    "matricule": "M-0042",
}


def line(**cells: Any) -> tuple[Any, ...]:
    """Give a row of an extraction under ``HEADERS``: valid but for the cells given, by name."""
    named = {**VALID, **cells}
    return tuple(named[name] for name in VALID)


def in_progress(stage: Scene, code: str = CODE) -> str:
    """Put the project of the stage In progress under a code, around the service; give it."""
    project_id = stage.project["project_id"]
    put_in_state(stage.owner, project_id, "in_progress", code=code)
    return project_id


def subproject(api: ContractClient, stage: Scene, code: str = SUBPROJECT) -> str:
    """Create a subproject of the project of the stage as its manager does; give it."""
    response = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": f"Lot {code}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["subproject_id"]


def opening(api: ContractClient, stage: Scene, content: bytes, **body: Any) -> Any:
    """Deposit an extraction and open its import as the manager does; give the answer."""
    upload_id = deposited(api, stage.manager, content)
    return api.post(
        f"{PROJECTS}/{stage.project['project_id']}/imports",
        headers=stage.manager.headers,
        json={"kind": "actual_costs", "upload_id": upload_id, **body},
    )


def analysed(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> dict[str, Any]:
    """Open the import of an extraction and run its analysis; give the import, as read."""
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, response.json()["import_id"])
    assert found["status"] == "analysed", found
    return found


def untouched(database: Database) -> tuple[int, int]:
    """Count the imports and the lines of cost of the platform: what a refusal leaves."""
    with database.transaction() as session:
        imports = len(session.scalars(select(ImportReport.id)).all())
        lines = len(session.scalars(select(CostLine.id)).all())
    return imports, lines
