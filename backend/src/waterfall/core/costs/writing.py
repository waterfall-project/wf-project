# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writing of a line of cost on its document and its item, private to the module.

One writing serves the application of an extraction (``applying``) and the loader of the witness
(``load_cost_lines``), so that neither forgets what the other does (EP-09, "Les coûts réels"): a
line of the project of the same document and the same item, no item included, is updated — its
date, its amount, its code and its imputation computed again, its columns kept replaced, its
exclusion intact —, another inserted, tracked; each names the import that wrote it last, and the
author and the instant of its write (WF-INTF-0140, WF-DAT-0110, WF-DAT-0070).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The most document numbers one read asks for.
_READ_BY = 10_000

# What identifies a line in its project: its document and its item, none included.
type DocumentKey = tuple[str, str | None]


class Written(Protocol):
    """A line to write: its document and its item, its date, its amount, its code, its columns."""

    @property
    def document_number(self) -> str:
        """The number of the document, which identifies the line with its item."""
        ...

    @property
    def document_item(self) -> str | None:
        """The item of the document, none when the extraction gives none."""
        ...

    @property
    def document_date(self) -> date:
        """The date of the document."""
        ...

    @property
    def amount(self) -> Decimal:
        """The amount, signed."""
        ...

    @property
    def subproject_code(self) -> str | None:
        """The code of subproject the WBS element bears, none without a subproject part."""
        ...

    @property
    def passthrough(self) -> Mapping[str, str]:
        """The columns kept, texts by their label."""
        ...


def held_lines(
    session: Session, project_id: UUID, numbers: Collection[str]
) -> dict[DocumentKey, CostLine]:
    """Read the lines of a project bearing one of these document numbers, by document and item.

    Only the documents of the file are read, not the whole project, in reads of at most
    ``_READ_BY`` numbers so that no read carries more parameters than the driver allows.
    """
    found: dict[DocumentKey, CostLine] = {}
    asked = sorted(set(numbers))
    for start in range(0, len(asked), _READ_BY):
        rows = session.scalars(
            select(CostLine).where(
                CostLine.project_id == project_id,
                CostLine.document_number.in_(asked[start : start + _READ_BY]),
            )
        )
        found.update({(row.document_number, row.document_item): row for row in rows})
    return found


@dataclass(frozen=True, slots=True)
class Placed:
    """Where a line is written: its project, its identifier if new, its subproject, its import.

    The subproject is the one its code names: none for a code no subproject bears, or no code.
    """

    project_id: UUID
    line_id: UUID
    subproject_id: UUID | None
    cost_import_id: UUID


def write_line(
    session: Session, held: CostLine | None, line: Written, placed: Placed, act: Act
) -> CostLine:
    """Write a line on its document and item: ``held`` updated, or a new one inserted, tracked."""
    row = held
    if row is None:
        row = CostLine(
            id=placed.line_id,
            project_id=placed.project_id,
            document_number=line.document_number,
            document_item=line.document_item,
            is_in_tracked_scope=True,
            excluded_reason=None,
            created_at=act.at,
            created_by=act.author,
        )
        session.add(row)
    row.document_date = line.document_date
    row.amount = line.amount
    row.subproject_code = line.subproject_code
    row.subproject_id = placed.subproject_id
    row.passthrough = dict(line.passthrough)
    row.last_import_id = placed.cost_import_id
    row.updated_at = act.at
    row.updated_by = act.author
    return row
