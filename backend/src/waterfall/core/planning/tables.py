# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the planning, private to the module (§4.4.1; EP-06, "Tables et migrations").

Regime "revised", partitioned by project as the cost structures (WF-DAT-0050): the nodes of a
structure, one collection for its two facets (``kind``, the task here, the estimate line by EP-07,
whose facet is a table of its module), the facet task, and the links between tasks. Regime
"project": the named timelines of a project and the inscriptions of the tasks, by their lineage, to
a timeline or to the time/time tracking of a milestone.

Every key refuses (``RESTRICT``), but inside a current revision, where the §4.4.1 lets the deletion
cascade: the facet follows its node, a link either of its tasks, a node its structure and its
parent, an inscription its timeline. A marked revision deletes nothing: the triggers of the
migration refuse any write of a row of a marked revision before any cascade, owner included, as
they do for the cost structures. The order of a node among its siblings is its ``rank``, unique
under its parent by kind — the roots, whose parent is null, included —, checked at the end of the
statement so that a renumbering of the siblings passes; ``position`` and ``row_number`` are
computed at the reading.
"""

from datetime import date, datetime
from decimal import Decimal
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The kinds of a node (``NodeKind``), the modes, the units, the states and the types of the
# contract (``SchedulingMode``, ``DurationUnit``, ``LagUnit``, ``TaskProgress``, ``LinkType``), and
# the kinds of an inscription (``TrackingEntry.kind``).
NODE_KINDS = ("task", "estimate_line")
SCHEDULING_MODES = ("automatic", "manual")
DURATION_UNITS = ("min", "h", "d", "w", "mo", "emin", "eh", "ed", "ew", "emo")
LAG_UNITS = (*DURATION_UNITS, "percent")
PROGRESSES = ("not_started", "started", "completed")
LINK_TYPES = ("finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish")
TRACKING_KINDS = ("timeline", "milestone_tracking")
# The bounds of the contract on a label of a task, an identifier given by MS Project, and a label
# of a timeline; the hours of a day.
LABEL_LENGTH = 300
EXTERNAL_ID_LENGTH = 200
TIMELINE_LABEL_LENGTH = 200
DAY_HOURS = 24
# The clause of the partitioning of every revised table.
BY_PROJECT = "LIST (project_id)"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _in_structure(column: str, *, first: bool = False) -> ForeignKeyConstraint:
    """Name a node of the structure of the row, which the row follows (migration 0022).

    ``first`` puts the project first, so that the key is named after the project, not the column.
    """
    columns = ["project_id", column] if first else [column, "project_id"]
    referred = ["node.project_id", "node.id"] if first else ["node.id", "node.project_id"]
    return ForeignKeyConstraint(
        [*columns, "structure_id"], [*referred, "node.structure_id"], ondelete="CASCADE"
    )


def _in_revision() -> ForeignKeyConstraint:
    """Name the structure of a revised row with its revision, which it follows (migration 0022).

    The structure names its revision in turn, which refuses: the row is of one revision, and of a
    structure of that revision.
    """
    return ForeignKeyConstraint(
        ["project_id", "structure_id", "revision_id"],
        ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
        ondelete="CASCADE",
    )


def _hours(column: str) -> CheckConstraint:
    """Bound the working hours elapsed on a day, from 0 to 24 (``WorkInstant.hours``)."""
    return CheckConstraint(f"{column} BETWEEN 0 AND {DAY_HOURS}", name=f"{column}_of_a_day")


class Stamped(Base):
    """The columns of audit of a row (WF-DAT-0070), its author an account or the platform if null.

    Abstract: each table that has them declares them as its own.
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class Node(Stamped):
    """A node of a structure: a task here, an estimate line by EP-07, under its parent.

    Its facet names it with its kind (``uq_node_project_id``), so that a node never receives the
    facet of another kind; its facet, its children and the links of its task name it with its
    structure (``uq_node_id``), so that none binds two structures — the facet task keeping a work
    package or an order item on a single task of a structure (``task``) —, and its structure is
    named with its revision, so that a node never binds a revision to the structure of another.
    ``lineage_id`` is kept by the copy of the revision (WF-DAT-0030); ``origin_risk_id`` is the risk
    a provision line comes from, null here (EP-08).
    """

    __tablename__ = "node"
    __table_args__ = (
        _in_revision(),
        _in_structure("parent_id", first=True),
        CheckConstraint(_in("kind", NODE_KINDS), name="kind_known"),
        CheckConstraint("rank >= 1", name="rank_positive"),
        # What a facet names: the node with its kind; what a facet, a child and a link name: the
        # node with its structure.
        UniqueConstraint("project_id", "id", "kind"),
        UniqueConstraint("id", "project_id", "structure_id"),
        # The order among the siblings of a kind, the roots included, checked at the end of the
        # statement: a renumbering moves every sibling at once.
        UniqueConstraint(
            "structure_id",
            "parent_id",
            "kind",
            "rank",
            "project_id",
            postgresql_nulls_not_distinct=True,
            deferrable=True,
            initially="IMMEDIATE",
        ),
        Index(None, "revision_id"),
        Index(None, "parent_id"),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    structure_id: Mapped[UUID]
    lineage_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[UUID | None]
    rank: Mapped[int] = mapped_column(Integer)
    origin_risk_id: Mapped[UUID | None]
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")


class Task(Base):
    """The facet task of a node: what a task is, its dates and its float as last computed.

    The dates are kept as the engine computed them at the last write of the structure, the instant
    of which is the structure's (``cost_structure.scheduled_at``): a marked revision keeps its own.
    A manual task carries no float.
    """

    __tablename__ = "task"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "node_id", "kind"],
            ["node.project_id", "node.id", "node.kind"],
            ondelete="CASCADE",
        ),
        _in_structure("node_id"),
        CheckConstraint("kind = 'task'", name="kind_task"),
        *bounded("label", LABEL_LENGTH),
        CheckConstraint(_in("scheduling_mode", SCHEDULING_MODES), name="scheduling_mode_known"),
        CheckConstraint(_in("duration_unit", DURATION_UNITS), name="duration_unit_known"),
        CheckConstraint("duration_value >= 0", name="duration_value_not_negative"),
        _hours("start_hours"),
        _hours("finish_hours"),
        CheckConstraint(_in("progress", PROGRESSES), name="progress_known"),
        CheckConstraint(
            "progress = 'not_started' OR started_on IS NOT NULL", name="started_on_when_started"
        ),
        CheckConstraint(
            "(completed_on IS NOT NULL) = (progress = 'completed')",
            name="completed_on_when_completed",
        ),
        CheckConstraint(
            f"char_length(external_id) <= {EXTERNAL_ID_LENGTH}", name="external_id_length"
        ),
        CheckConstraint(
            "order_item_id IS NULL OR work_package_id IS NULL", name="one_work_breakdown_item"
        ),
        # A work package or an order item is borne by one task of a structure at most.
        Index(
            "uq_task_order_item",
            "project_id",
            "structure_id",
            "order_item_id",
            unique=True,
            postgresql_where=text("order_item_id IS NOT NULL"),
        ),
        Index(
            "uq_task_work_package",
            "project_id",
            "structure_id",
            "work_package_id",
            unique=True,
            postgresql_where=text("work_package_id IS NOT NULL"),
        ),
        Index(None, "order_item_id"),
        Index(None, "work_package_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    node_id: Mapped[UUID] = mapped_column(primary_key=True)
    structure_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    description: Mapped[str | None] = mapped_column(Text)
    scheduling_mode: Mapped[str] = mapped_column(Text)
    duration_value: Mapped[Decimal] = mapped_column(Numeric)
    duration_unit: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    start_hours: Mapped[Decimal] = mapped_column(Numeric)
    finish_date: Mapped[date] = mapped_column(Date)
    finish_hours: Mapped[Decimal] = mapped_column(Numeric)
    progress: Mapped[str] = mapped_column(Text)
    started_on: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)
    external_id: Mapped[str | None] = mapped_column(Text)
    order_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("order_item.id", ondelete="RESTRICT")
    )
    work_package_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("work_package.id", ondelete="RESTRICT")
    )
    total_float_days: Mapped[Decimal | None] = mapped_column(Numeric)
    is_critical: Mapped[bool] = mapped_column(Boolean)


class TaskLink(Base):
    """A link between two tasks of a structure, its lag in the unit of its entry (WF-PLA-0030).

    Two tasks of its structure are linked once at most. The absence of a loop and of a link between
    a summary task and its subordinate is the service's to keep; ``in_conflict`` is the engine's
    (WF-PLA-0100).
    """

    __tablename__ = "task_link"
    __table_args__ = (
        _in_revision(),
        _in_structure("predecessor_id"),
        _in_structure("successor_id"),
        CheckConstraint("predecessor_id <> successor_id", name="predecessor_not_successor"),
        CheckConstraint(_in("link_type", LINK_TYPES), name="link_type_known"),
        CheckConstraint(_in("lag_unit", LAG_UNITS), name="lag_unit_known"),
        UniqueConstraint("structure_id", "predecessor_id", "successor_id", "project_id"),
        Index(None, "predecessor_id"),
        Index(None, "successor_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    structure_id: Mapped[UUID]
    predecessor_id: Mapped[UUID]
    successor_id: Mapped[UUID]
    link_type: Mapped[str] = mapped_column(Text)
    lag_value: Mapped[Decimal] = mapped_column(Numeric)
    lag_unit: Mapped[str] = mapped_column(Text)
    in_conflict: Mapped[bool] = mapped_column(Boolean)


class Timeline(Stamped):
    """A named timeline of a project, to which tasks are inscribed (WF-PLA-0140).

    Its label is not unique; it is deleted for good, its inscriptions with it.
    """

    __tablename__ = "timeline"
    __table_args__ = (
        *bounded("label", TIMELINE_LABEL_LENGTH),
        Index(None, "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))


class TrackingEntry(Stamped):
    """An inscription of a task, by its lineage, to a timeline or to the time/time tracking.

    Kept by lineage, it follows the task from revision to revision (WF-PLA-0060). A lineage is
    inscribed once to the time/time tracking, whose timeline is null, and once to each timeline.
    """

    __tablename__ = "tracking_entry"
    __table_args__ = (
        CheckConstraint(_in("kind", TRACKING_KINDS), name="kind_known"),
        CheckConstraint(
            "(timeline_id IS NOT NULL) = (kind = 'timeline')", name="timeline_when_timeline"
        ),
        UniqueConstraint("lineage_id", "kind", "timeline_id", postgresql_nulls_not_distinct=True),
        Index(None, "project_id"),
        Index(None, "timeline_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    lineage_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    timeline_id: Mapped[UUID | None] = mapped_column(ForeignKey("timeline.id", ondelete="CASCADE"))
