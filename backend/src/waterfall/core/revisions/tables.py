# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the revisions, private to the module (§4.4.1, regimes "project" and "revised").

A revision of a project — at most one current (``draft``) per project, marked for good afterwards
(WF-REV-0020) — and the first table of the revised, its cost structures. A revised table is
partitioned by list on ``project_id``, one partition per project, created with it by the function
``create_project_partitions`` of the owner of the tables (migration ``0020``, WF-DAT-0050): its
key holds the key of the partition, and its row names its revision with its project, so that it
lives in the partition of its revision's project. The function reads the revised tables in the
catalogue since ``0026``: a table that an epic adds, partitioned by list on ``project_id``, has its
partitions created without replacing it, given its trigger ``<table>_refuse_truncate``.

What the database itself refuses of a marked revision — going back to ``draft``, any change but
its designation as reference, its counter and its audit — and of a row of a marked revision —
any write — is said by the triggers of the migration, owner included.
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
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The statuses of a revision and the kinds of a structure (``RevisionStatus``, ``StructureKind``):
# the main one, an amendment (a differential), the own estimate of a risk (EP-08), and the base of a
# differential, which no operation serves (US-3050, migration ``0038``).
STATUSES = ("draft", "marked")
STRUCTURE_KINDS = ("main", "amendment", "risk", "base")
# The bounds the contract puts on a name of version and on a label of structure, and on a year.
VERSION_NAME_LENGTH = 100
LABEL_LENGTH = 300
YEARS = (2000, 2100)
# The clause of the partitioning of every revised table.
BY_PROJECT = "LIST (project_id)"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Audited(Base):
    """The columns of audit and the counter of the writes of a row that changes (WF-DAT-0070).

    An author is an account, or the platform when null: the loader of the witness, the worker.
    Abstract: each table that has them declares them as its own.
    """

    __abstract__ = True

    # The database default stays 0, as in every other table of the platform: a resource is born at
    # ``FIRST_VERSION`` (1), which the code of the module writes on insert and never leaves to this
    # default. Moving it to 1 here alone would split the schema; #2762 settles it for all tables.
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class Revision(Audited):
    """A revision of a project: current while ``draft``, immutable once ``marked``.

    Its name of version is entered at the marking, unique among the marked revisions of its
    project; the moment of the marking is there if and only if it is marked. At most one revision
    of a project is its reference (WF-REV-0040). ``lineage_id`` is the identifier of its lineage
    (WF-DAT-0030).
    """

    __tablename__ = "revision"
    __table_args__ = (
        CheckConstraint(_in("status", STATUSES), name="status_known"),
        *bounded("version_name", VERSION_NAME_LENGTH),
        CheckConstraint(
            "status <> 'marked' OR version_name IS NOT NULL", name="version_name_when_marked"
        ),
        CheckConstraint(
            "(marked_at IS NOT NULL) = (status = 'marked')", name="marked_at_when_marked"
        ),
        CheckConstraint(
            f"reference_year BETWEEN {YEARS[0]} AND {YEARS[1]}", name="reference_year_bound"
        ),
        # What a row of a revised table names: the revision with its project (its partition).
        UniqueConstraint("project_id", "id"),
        # The source is a revision of the same project, and never the revision itself.
        ForeignKeyConstraint(
            ["project_id", "source_revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("source_revision_id <> id", name="source_not_self"),
        Index(
            "uq_revision_draft",
            "project_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
        Index(
            "uq_revision_version_name",
            "project_id",
            "version_name",
            unique=True,
            postgresql_where=text("status = 'marked'"),
        ),
        Index(
            "uq_revision_reference",
            "project_id",
            unique=True,
            postgresql_where=text("is_reference"),
        ),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("project.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(Text)
    # Null until the marking (``Revision.version_name`` of the contract).
    version_name: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    description: Mapped[str | None] = mapped_column(Text)
    marked_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    reference_year: Mapped[int] = mapped_column(SmallInteger)
    is_reference: Mapped[bool] = mapped_column(Boolean)
    lineage_id: Mapped[UUID]
    # The marked revision this one is the copy of; null for the first revision of a project, kept
    # after the marking (``Revision.source_revision_id`` of the contract).
    source_revision_id: Mapped[UUID | None]
    # The rate of inflation and the probability of winning of the project, kept at the marking
    # (EP-07); null on a current revision, which follows its project, and on one marked before.
    inflation_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    win_probability: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class CostStructure(Audited):
    """A cost structure of a revision: its main one, its amendments, its risks' own (WF-REV-0100).

    The first revised table, partitioned by project. A revision has one main structure; the own
    estimate of a risk names its risk (``risk_id``, there for that kind alone), one at most by risk
    and by revision (EP-08, migration ``0035``). The base of a differential names its differential
    (``differential_id``, there for that kind alone), of the same revision, one base at most by
    differential; a differential keeps the counter the main structure bore when its base was taken
    (``main_lock_version``, there for that kind and the own estimate of a risk alone): it is up to
    date while the main structure bears it (US-3050, migration ``0038``). An own estimate pruned
    names the marked revision its differences are exact against (``pruned_revision_id``, EP-30,
    migration ``0044``), and what it abandons is kept apart (``OwnEstimateAbandonment``).
    ``lineage_id`` is kept by the copy of the revision, its own identifier at the creation of the
    structure (WF-DAT-0030). The date its
    planning starts on and the instant its dates were computed (EP-06, #2170) are null for a row
    the migration ``0023`` did not fill, which the code reads as their derived values: the day of
    the creation of the origin of its lineage, the instant of its own creation.
    """

    __tablename__ = "cost_structure"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        # The risk of an own estimate, with its project; it refuses (EP-08).
        ForeignKeyConstraint(
            ["project_id", "risk_id"], ["risk.project_id", "risk.id"], ondelete="RESTRICT"
        ),
        CheckConstraint(_in("kind", STRUCTURE_KINDS), name="kind_known"),
        CheckConstraint("(risk_id IS NOT NULL) = (kind = 'risk')", name="risk_of_its_kind"),
        # The differential of a base, with its revision; it refuses (US-3050).
        ForeignKeyConstraint(
            ["project_id", "differential_id", "revision_id"],
            ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(differential_id IS NOT NULL) = (kind = 'base')", name="differential_of_its_kind"
        ),
        # A differential and the own estimate of a risk keep it alike (US-3050, EP-30).
        CheckConstraint(
            "(main_lock_version IS NOT NULL) = (kind IN ('amendment', 'risk'))",
            name="main_counter_of_its_kind",
        ),
        # A differential copied out of date keeps 0, which the main structure never bears.
        CheckConstraint("main_lock_version >= 0", name="main_counter_not_negative"),
        # The marked revision an own estimate pruned is exact against, with its project (EP-30);
        # the revision first, which names the key apart from the one of the revision of the row.
        ForeignKeyConstraint(
            ["pruned_revision_id", "project_id"],
            ["revision.id", "revision.project_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("pruned_revision_id IS NULL OR kind = 'risk'", name="pruned_of_its_kind"),
        *bounded("label", LABEL_LENGTH),
        # What a revised row of the planning names: the structure with its revision (EP-06).
        UniqueConstraint("project_id", "id", "revision_id"),
        # What the evaluation of a risk names: its own estimate, with its revision and its risk.
        UniqueConstraint("risk_id", "id", "revision_id", "project_id"),
        Index(None, "project_id", "revision_id"),
        Index(
            "uq_cost_structure_main",
            "project_id",
            "revision_id",
            unique=True,
            postgresql_where=text("kind = 'main'"),
        ),
        Index(
            "uq_cost_structure_risk",
            "project_id",
            "revision_id",
            "risk_id",
            unique=True,
            postgresql_where=text("kind = 'risk'"),
        ),
        Index(
            "uq_cost_structure_base",
            "project_id",
            "differential_id",
            unique=True,
            postgresql_where=text("kind = 'base'"),
        ),
        counted(),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    is_merged: Mapped[bool] = mapped_column(Boolean)
    lineage_id: Mapped[UUID]
    planning_start_on: Mapped[date | None] = mapped_column(Date)
    scheduled_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # The risk whose own estimate the structure is; null for any other kind.
    risk_id: Mapped[UUID | None]
    # The differential whose base the structure is; null for any other kind (US-3050).
    differential_id: Mapped[UUID | None]
    # The counter the main structure bore when the base of the differential, or of the own estimate
    # of a risk, was taken or last carried over, 0 when it bore none in this revision (one taken up
    # out of date); null for any other kind.
    main_lock_version: Mapped[int | None] = mapped_column(Integer)
    # The marked revision against whose main structure the differences of an own estimate pruned
    # are exact; null for an own estimate whole, and for any other kind (EP-30).
    pruned_revision_id: Mapped[UUID | None]


class OwnEstimateAbandonment(Base):
    """What the own estimate of a risk, pruned, abandons of the main structure (EP-30).

    A node, by its lineage, or a link, by the lineages of its two tasks (WF-DAT-0030): what the
    pruning keeps of a removal, the nodes it removes being deleted with the rest. Revised, of the
    revision of its structure; written once, by the pruning, taken up by the copy of a revision,
    and deleted with its structure, by the abandonment of a revision or the deletion of its risk.
    """

    __tablename__ = "own_estimate_abandonment"
    __table_args__ = (
        # The own estimate, with its revision: a structure of the revision of the row.
        ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id"],
            ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
            ondelete="RESTRICT",
        ),
        # A node or a link, never both, a link by its two tasks.
        CheckConstraint(
            "(node_lineage_id IS NULL) = (predecessor_lineage_id IS NOT NULL) "
            "AND (predecessor_lineage_id IS NULL) = (successor_lineage_id IS NULL)",
            name="node_or_link",
        ),
        # A node or a link abandoned once by an own estimate; each led by its own column, which
        # names the constraint apart, the key of the partition held.
        UniqueConstraint("node_lineage_id", "structure_id", "project_id"),
        UniqueConstraint(
            "predecessor_lineage_id", "successor_lineage_id", "structure_id", "project_id"
        ),
        # The abandonments of a revision: its abandonment deletes them, its copy reads them.
        Index(None, "revision_id"),
        {"postgresql_partition_by": BY_PROJECT},
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID]
    structure_id: Mapped[UUID]
    node_lineage_id: Mapped[UUID | None]
    predecessor_lineage_id: Mapped[UUID | None]
    successor_lineage_id: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
