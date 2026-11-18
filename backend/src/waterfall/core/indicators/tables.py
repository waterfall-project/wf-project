# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the indicators, private to the module (§4.4.1, regime "revised"; EP-10).

What a revision keeps of its indicators at its marking (WF-DAT-0040): one JSON document by
revision, kind and scope — the answer of the contract of its kind for its scope, as the marking
computed it, every zone null —, partitioned by project as the cost structures (WF-DAT-0050). A row
is written by the marking alone, while its revision is still current, and never changed nor deleted
after: the triggers of the migration ``0032`` refuse it, owner included. Its key names its revision
with its project, and refuses (``RESTRICT``).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded

# The kinds of document a marking keeps (EP-10, "Tables et migrations"): the indicators of the
# estimate and of the remaining to commit, those of the project, and its three curves; then the
# documents of a project the portfolio sums (EP-11, migration ``0037``).
KINDS = (
    "estimate",
    "remaining",
    "project",
    "cost_curve",
    "cost_curve_payment_delays",
    "earned_value_curves",
    "portfolio_workload",
    "portfolio_cost_structure",
    "portfolio_risks",
    "portfolio_milestones",
    "portfolio_offer_curves",
)
# The longest scope: ``project``, ``unassigned``, or the identifier of a subproject in text.
SCOPE_LENGTH = 36
# The clause of the partitioning of every revised table.
BY_PROJECT = "LIST (project_id)"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class RevisionIndicator(Base):
    """A document of indicators a revision keeps: its kind, its scope, when it was computed.

    ``computed_at`` is the instant of the marking, ``created_by`` its requester, or the platform
    when null.
    """

    __tablename__ = "revision_indicator"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(_in("kind", KINDS), name="kind_known"),
        *bounded("scope", SCOPE_LENGTH),
        CheckConstraint("jsonb_typeof(document) = 'object'", name="document_object"),
        UniqueConstraint("project_id", "revision_id", "kind", "scope"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
