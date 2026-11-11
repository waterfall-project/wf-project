# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the revisions, private to the module (§4.4.1, regimes "project" and "revised").

A revision of a project — at most one current (``draft``) per project, marked for good afterwards
(WF-REV-0020) — and the first table of the revised, its cost structures. A revised table is
partitioned by list on ``project_id``, one partition per project, created with it by the function
``create_project_partitions`` of the owner of the tables (migration ``0020``, WF-DAT-0050): its
key holds the key of the partition, and its row names its revision with its project, so that it
lives in the partition of its revision's project. Each epic that adds a revised table replaces
that function in its migration.

What the database itself refuses of a marked revision — going back to ``draft``, any change but
its designation as reference, its counter and its audit — and of a row of a marked revision —
any write — is said by the triggers of the migration, owner included.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The statuses of a revision and the kinds of structure EP-04 writes (``RevisionStatus``; the main
# structure of ``StructureKind`` alone: the amendments and the risks' own come with EP-08).
STATUSES = ("draft", "marked")
STRUCTURE_KINDS = ("main",)
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


class CostStructure(Audited):
    """A cost structure of a revision: its main one alone here (WF-REV-0100), one per revision.

    The first revised table, partitioned by project. ``lineage_id`` is kept by the copy of the
    revision, its own identifier at the creation of the structure (WF-DAT-0030). The date its
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
        CheckConstraint(_in("kind", STRUCTURE_KINDS), name="kind_known"),
        *bounded("label", LABEL_LENGTH),
        # What a revised row of the planning names: the structure with its revision (EP-06).
        UniqueConstraint("project_id", "id", "revision_id"),
        Index(None, "project_id", "revision_id"),
        Index(
            "uq_cost_structure_main",
            "project_id",
            "revision_id",
            unique=True,
            postgresql_where=text("kind = 'main'"),
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
