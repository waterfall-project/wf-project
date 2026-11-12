# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the actual costs share (EP-09, "Les tests du back"): the log and the lines.

The rows of the actual costs written around the service — the import of the exchanges an entry of
the log names, the entry, a line of cost —, each valid unless a test changes it, as
``estimate_support`` writes those of the estimate; and an import applied on a project, with the
account that confirmed it. The stories of EP-09 add here the lines of cost loaded through the
interface of the actual costs (``load_cost_import``, ``load_cost_lines``: ``cost``, ``load_import``,
US-1610/L3) and the clock set; a story that needs another helper writes it in its own file.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from project_rows import AT, STAMP
from sqlalchemy import insert
from support import raw_account

from waterfall.core.costs.interface import (
    CostImportLoad,
    CostLineLoad,
    load_cost_import,
    load_cost_lines,
)
from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from collections.abc import Sequence

    from projects_support import Scene
    from sqlalchemy.engine import Connection


def report_row(project_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of an import of the actual costs of a project, applied, period of April."""
    return {
        "id": uuid4(),
        "project_id": project_id,
        "kind": "actual_costs",
        "filename": "extraction-avril.xlsx",
        "upload_id": uuid4(),
        "object_key": f"uploads/{uuid4()}",
        "period_from": date(2026, 4, 1),
        "period_to": date(2026, 4, 30),
        "status": "applied",
        "created_at": AT,
        "analysed_at": AT,
        "expires_at": AT + timedelta(days=1),
        "applied_at": AT,
        **overrides,
    }


def cost_import_row(
    project_id: UUID, report_id: UUID, account_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of the entry of the log an import wrote: two lines created, one rejected."""
    return {
        "id": uuid4(),
        "project_id": project_id,
        "import_report_id": report_id,
        "imported_at": AT,
        "requested_by": account_id,
        "period_from": date(2026, 4, 1),
        "period_to": date(2026, 4, 30),
        "created_count": 2,
        "updated_count": 0,
        "unchanged_count": 0,
        "rejected_count": 1,
        "passthrough_columns": ["Fournisseur", "Libellé"],
        **overrides,
    }


def cost_line_row(project_id: UUID, import_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of a line of cost of a project, tracked, imputed to the project alone."""
    return {
        "id": uuid4(),
        "project_id": project_id,
        "subproject_id": None,
        "subproject_code": None,
        "document_number": "5100001234",
        "document_item": None,
        "document_date": date(2026, 4, 2),
        "amount": Decimal("1250.00"),
        "is_in_tracked_scope": True,
        "excluded_reason": None,
        "passthrough": {"Fournisseur": "Atelier Durand", "Libellé": "Usinage"},
        "last_import_id": import_id,
        **STAMP,
        **overrides,
    }


@dataclass(frozen=True)
class Imported:
    """An import of the actual costs applied on a project: the account, the import, its entry."""

    project_id: UUID
    account_id: UUID
    report_id: UUID
    cost_import_id: UUID


def write_import(connection: Connection, project_id: UUID) -> Imported:
    """Write an import applied on a project, the account that confirmed it and its entry."""
    account, report, entry = uuid4(), uuid4(), uuid4()
    email = f"{account.hex}@example.org"
    connection.execute(insert(UserAccount).values(**raw_account(id=account, email=email)))
    connection.execute(insert(ImportReport).values(**report_row(project_id, id=report)))
    connection.execute(
        insert(CostImport).values(**cost_import_row(project_id, report, account, id=entry))
    )
    return Imported(project_id, account, report, entry)


def insert_cost_line(connection: Connection, imported: Imported, **overrides: object) -> UUID:
    """Write a line of cost the import brought; give it."""
    row = cost_line_row(imported.project_id, imported.cost_import_id, **overrides)
    connection.execute(insert(CostLine).values(**row))
    line_id = row["id"]
    assert isinstance(line_id, UUID)
    return line_id


def cost(
    number: str, code: str | None, amount: str = "100.00", item: str | None = None
) -> CostLineLoad:
    """Give a line an import loads: its document, its code of subproject, its amount, its item."""
    return CostLineLoad(
        cost_line_id=uuid4(),
        document_number=number,
        document_item=item,
        document_date=date(2026, 4, 2),
        amount=Decimal(amount),
        subproject_code=code,
        passthrough={"Fournisseur": "Câbles du Rhône"},
    )


def load_import(
    stage: Scene,
    project_id: UUID,
    lines: Sequence[CostLineLoad],
    *,
    at: datetime = AT,
    author: UUID | None = None,
) -> UUID:
    """Load an import applied on a project by the interface: its entry, then its lines; give it.

    The import of the exchanges it names written around the service, applied; the entry confirmed
    by ``author``, the manager of the stage unless said, at ``at``, its lines all counted created.
    """
    author = author or stage.manager.user_id
    report = uuid4()
    with stage.owner.begin() as connection:
        connection.execute(insert(ImportReport).values(**report_row(project_id, id=report)))
    entry = CostImportLoad(
        cost_import_id=uuid4(),
        import_report_id=report,
        imported_at=at,
        requested_by=author,
        period_from=date(2026, 4, 1),
        period_to=date(2026, 4, 30),
        created_count=len(lines),
        updated_count=0,
        unchanged_count=0,
        rejected_count=0,
        passthrough_columns=("Fournisseur",),
    )
    with stage.database.transaction() as session:
        load_cost_import(session, project_id, entry)
        load_cost_lines(session, project_id, entry.cost_import_id, lines, Act(author, at))
    return entry.cost_import_id
