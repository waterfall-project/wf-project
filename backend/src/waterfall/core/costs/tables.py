# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the actual costs, private to the module (§4.4.1, regime "project"; EP-09).

A line of the actual costs of a project (``CostLine``), one per document and item — a null item a
value like any other (WF-DAT-0110, WF-INTF-0140) —, imputed to a subproject of its project or to
the project alone, tracked or excluded; and the log of the imports that wrote them
(``CostImport``), one per import of the exchanges, never changed. Neither is partitioned, nor ever
deleted: every key refuses (``RESTRICT``). A line names its subproject with its project, so that it
never names one of another.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded

# The bounds of a document number and of the code of a subproject read in a WBS element
# (``ActualCostLine.subproject_code``, 50 characters whether or not a subproject bears it).
DOCUMENT_NUMBER_LENGTH = 200
SUBPROJECT_CODE_LENGTH = 50
# The four counts of an import (``CostImport``).
COUNTS = ("created_count", "updated_count", "unchanged_count", "rejected_count")
# What a JSON value holds: an object whose values are texts, an array whose elements are texts.
TEXTS_BY_NAME = (
    "jsonb_typeof({0}) = 'object' AND NOT jsonb_path_exists({0}, '$.* ? (@.type() != \"string\")')"
)
TEXTS_IN_ORDER = (
    "jsonb_typeof({0}) = 'array' AND NOT jsonb_path_exists({0}, '$[*] ? (@.type() != \"string\")')"
)


def _not_negative(column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} >= 0", name=f"{column}_not_negative")


class CostImport(Base):
    """An entry of the log of the imports of the actual costs of a project (WF-CRE-0050).

    Written once, at the application of an import, and never changed: its instant and the account
    that confirmed it stand for its audit, as for a transition of state. Its period is the one the
    import declared, either end absent; its columns kept, those of the file, in their order.
    """

    __tablename__ = "cost_import"
    __table_args__ = (
        CheckConstraint("period_from <= period_to", name="period_ordered"),
        *(_not_negative(count) for count in COUNTS),
        CheckConstraint(
            TEXTS_IN_ORDER.format("passthrough_columns"), name="passthrough_columns_texts"
        ),
        # An import of the exchanges is applied once.
        UniqueConstraint("import_report_id"),
        # The log of a project, the most recent first (``listCostImports``).
        Index(None, "project_id", "imported_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    import_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_report.id", ondelete="RESTRICT")
    )
    imported_at: Mapped[datetime] = mapped_column(UtcDateTime)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="RESTRICT"))
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    created_count: Mapped[int] = mapped_column(Integer)
    updated_count: Mapped[int] = mapped_column(Integer)
    unchanged_count: Mapped[int] = mapped_column(Integer)
    rejected_count: Mapped[int] = mapped_column(Integer)
    passthrough_columns: Mapped[list[str]] = mapped_column(JSONB)


class CostLine(Base):
    """A line of the actual costs of a project, by its document and its item (WF-CRE-0010).

    Its subproject is the one its code names in its project, null for a line without a subproject
    part or with a code no subproject bears, which keeps its code (WF-CRE-0020). An excluded line
    may say why; a tracked one never does (WF-CRE-0030). Its columns kept are texts by their name.
    An import inserts or updates it on its document and item, an exclusion updates it: no counter,
    its audit alone.
    """

    __tablename__ = "cost_line"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        *bounded("document_number", DOCUMENT_NUMBER_LENGTH),
        CheckConstraint(
            f"char_length(subproject_code) <= {SUBPROJECT_CODE_LENGTH}",
            name="subproject_code_length",
        ),
        CheckConstraint(
            "excluded_reason IS NULL OR NOT is_in_tracked_scope",
            name="excluded_reason_when_excluded",
        ),
        CheckConstraint(
            "subproject_id IS NULL OR subproject_code IS NOT NULL",
            name="subproject_code_when_imputed",
        ),
        CheckConstraint(TEXTS_BY_NAME.format("passthrough"), name="passthrough_texts"),
        # The idempotence of the imports, held by the base (WF-DAT-0110): two lines of the same
        # document and item, no item included, are one.
        UniqueConstraint(
            "project_id", "document_number", "document_item", postgresql_nulls_not_distinct=True
        ),
        # The reading by period and by subproject, and the imputation of the lines that wait for
        # the code of a subproject created (EP-09, "Tables et migrations"): each index leads by the
        # column the convention names it after, the project beside it.
        Index(None, "project_id", "document_date"),
        Index(None, "subproject_id", "project_id"),
        Index(None, "subproject_code", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    subproject_id: Mapped[UUID | None]
    subproject_code: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    document_number: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    document_item: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    document_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    is_in_tracked_scope: Mapped[bool] = mapped_column(Boolean)
    excluded_reason: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    passthrough: Mapped[dict[str, Any]] = mapped_column(JSONB)
    last_import_id: Mapped[UUID] = mapped_column(ForeignKey(CostImport.id, ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
