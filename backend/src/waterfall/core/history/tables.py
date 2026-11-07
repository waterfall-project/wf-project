# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the history, private to the module: technical rows (§4.4.1; EP-06).

An entry of the history that can be undone, by revision, account and session of sign-in (the
``sid`` of the token), with the rows it touched as they were and as they are; the plan of a paste
kept between its preview and its application, an hour at most. Both name their revision by a key
that refuses: the marking and the abandonment delete them first (``register_closing``).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from waterfall.platform.database import Base, UtcDateTime

# The kinds of a change undone (``UndoneKind``), and the columns a paste targets (``NodeColumn``),
# in the order of the contract.
UNDONE_KINDS = (
    "cell",
    "node_create",
    "node_delete",
    "node_move",
    "paste",
    "link",
    "progress",
    "remaining",
    "tracking",
    "structure_update",
    "risk_create",
    "risk_update",
    "risk_review",
    "risk_delete",
)
NODE_COLUMNS = (
    "label",
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "physical_progress",
    "total_float",
    "is_critical",
    "started_on",
    "completed_on",
    "predecessors",
    "work_breakdown",
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class UndoEntry(Base):
    """An entry of the history of a revision, for an account in a session of sign-in.

    ``before`` and ``after`` hold the rows of the nodes, tasks, links and inscriptions the entry
    touched, as the planning gives them (``snapshot``): the history reads no table of its own.
    """

    __tablename__ = "undo_entry"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(_in("kind", UNDONE_KINDS), name="kind_known"),
        UniqueConstraint("revision_id", "user_account_id", "session_id", "rank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    user_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    session_id: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(Text)
    node_ids: Mapped[list[UUID]] = mapped_column(ARRAY(Uuid))
    before: Mapped[Any] = mapped_column(JSONB)
    after: Mapped[Any] = mapped_column(JSONB)
    undone: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)


class PastePlan(Base):
    """The plan of a paste, kept between its preview and its application, an hour at most.

    ``structure_lock_version`` is the counter of the structure at the preview: an application on a
    structure that moved since is refused (412).
    """

    __tablename__ = "paste_plan"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(_in("target_column", NODE_COLUMNS), name="target_column_known"),
        CheckConstraint("structure_lock_version >= 0", name="structure_lock_version_not_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    structure_id: Mapped[UUID]
    user_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    target_node_id: Mapped[UUID]
    target_column: Mapped[str] = mapped_column(Text)
    rows: Mapped[Any] = mapped_column(JSONB)
    structure_lock_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
