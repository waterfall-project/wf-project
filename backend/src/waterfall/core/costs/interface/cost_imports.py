# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The log of the imports of the actual costs of a project (WF-CRE-0050; US-1610).

``list_cost_imports`` reads the entries of a project, the most recent first, each with its author,
its period and its four counts (``listCostImports``, US-1610/L2, whose application writes them);
``load_cost_import`` writes the entry of an import of the witness, at the identifier, the instant
and the author it imposes (US-1610/L3, for the tests and the witness of US-1650/L2): the import of
the exchanges it names is loaded before it, and the lines it brought after it (``load_cost_lines``).

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.costs.tables import CostImport

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class CostImportLoad:
    """An entry of the log the witness imposes: its identifier, its import, its instant, its author.

    Its period as the import declared it, its four counts as its application made them, and the
    columns of its file kept, in their order.
    """

    cost_import_id: UUID
    import_report_id: UUID
    imported_at: datetime
    requested_by: UUID
    period_from: date | None
    period_to: date | None
    created_count: int
    updated_count: int
    unchanged_count: int
    rejected_count: int
    passthrough_columns: tuple[str, ...] = ()


def list_cost_imports(session: Session, project_id: UUID) -> None:
    """Give the entries of the log of the imports of a project (``listCostImports``)."""
    msg = "list_cost_imports is filled by US-1610/L2"
    raise NotImplementedError(msg)


def load_cost_import(session: Session, project_id: UUID, load: CostImportLoad) -> None:
    """Write the entry of an import of the witness, at the identifier and the instant imposed.

    Written once, as the application writes it, and never changed; the base refuses an import of
    the exchanges applied twice, a period reversed and a count below nought.
    """
    session.add(
        CostImport(
            id=load.cost_import_id,
            project_id=project_id,
            import_report_id=load.import_report_id,
            imported_at=load.imported_at,
            requested_by=load.requested_by,
            period_from=load.period_from,
            period_to=load.period_to,
            created_count=load.created_count,
            updated_count=load.updated_count,
            unchanged_count=load.unchanged_count,
            rejected_count=load.rejected_count,
            passthrough_columns=list(load.passthrough_columns),
        )
    )
    session.flush()
