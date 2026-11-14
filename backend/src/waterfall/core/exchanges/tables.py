# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the exchanges, private to the module (§4.4.1, regime "project"; EP-06).

An import of a project and its report: its opening, the file deposited for it, where it stands,
its report in codes and parameters (``ImportReport``), the last background task that ran for it,
and, for a planning of MS Project in calendar gap, the rule its durations are converted by
(``duration_rule``, US-2000; null otherwise).
A deposit serves one import; the report outlives the file, which the purge or the abandonment
deletes (WF-DAT-0120). It is deleted at its expiry or its abandonment.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime

# The kinds of an import (``ExchangeKind``) and the states an import stands in (``Import.status``),
# in the order of the contract; those that keep the instant its report expires at.
EXCHANGE_KINDS = ("ms_project_schedule", "estimate", "remaining", "actual_costs")
IMPORT_STATUSES = (
    "analysing",
    "analysed",
    "applying",
    "applied",
    "abandoned",
    "expired",
    "failed",
    "refused",
)
EXPIRING = ("analysed", "applying", "applied", "abandoned", "expired")
# The rules of conversion of the durations of an MS Project schedule in calendar gap
# (``ImportDurationRule``, US-2000), in the order of the contract.
DURATION_RULES = ("keep_durations", "keep_dates")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ImportReport(Base):
    """An import of a project: its opening, its state, its report, its last task."""

    __tablename__ = "import_report"
    __table_args__ = (
        CheckConstraint(_in("kind", EXCHANGE_KINDS), name="kind_known"),
        CheckConstraint(_in("status", IMPORT_STATUSES), name="status_known"),
        # The name of the file deposited, bounded as the deposit bounds it (``file_upload``).
        CheckConstraint("char_length(filename) BETWEEN 1 AND 255", name="filename_length"),
        CheckConstraint(
            f"(expires_at IS NOT NULL) = ({_in('status', EXPIRING)})",
            name="expires_at_when_analysed",
        ),
        CheckConstraint("report IS NULL OR jsonb_typeof(report) = 'object'", name="report_object"),
        CheckConstraint(_in("duration_rule", DURATION_RULES), name="duration_rule_known"),
        # Only a planning of MS Project has a rule of its durations (WF-INTF-0040).
        CheckConstraint(
            "duration_rule IS NULL OR kind = 'ms_project_schedule'",
            name="duration_rule_of_a_planning",
        ),
        # A deposit serves one import.
        UniqueConstraint("upload_id"),
        Index(None, "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    upload_id: Mapped[UUID]
    object_key: Mapped[str] = mapped_column(Text)
    structure_id: Mapped[UUID | None]
    revision_id: Mapped[UUID | None]
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    task_id: Mapped[UUID | None]
    requested_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    analysed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    applied_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    duration_rule: Mapped[str | None] = mapped_column(Text)
