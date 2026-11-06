# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the projects, private to the module (§4.4.1, regime "project"; EP-04).

A project, the history of its states, its contributors, its subprojects and its work breakdown —
work packages, order items, deliverables. A project is never deleted: it leaves its cycle of life
by a terminal state (WF-CYC-0080). Its code, which the ERP knows it by, is a constraint of
uniqueness and never a key: every row that refers to a project holds its identifier, so its code
is corrected without touching any of them (WF-DAT-0060). The codes and the labels sort in the order
of the code points (collation ``C``), and are bounded and never blank as the contract bounds them.

The project names its reference revision and its current one, rows of the module of the
revisions, by keys that refuse, added once both tables exist (``use_alter``): the revision names
its project in return.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime, bounded, counted

# The six states of the cycle of life and the two kinds of contributor, as the contract says them
# (``ProjectState``, ``ContributorKind``).
STATES = ("created", "pricing", "in_progress", "completed", "lost", "abandoned")
CONTRIBUTOR_KINDS = ("project_manager", "contributor")
# The bounds the contract puts on a project's code and label (``ProjectCode``, ``Project.label``),
# and on a subproject's code (``DeclaredSubprojectCode``).
CODE_LENGTH = 50
LABEL_LENGTH = 300
SUBPROJECT_CODE_LENGTH = 31
# The characters the name of a tab of a workbook may not hold, which a subproject's code names
# (ANNEXE B, WF-PRJ-0050), as a class of a regular expression of PostgreSQL.
TAB_FORBIDDEN = r"[:\\/?*\[\]]"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _ratio(column: str) -> CheckConstraint:
    """Bound a ratio of the project, its rate of inflation or its probability of winning."""
    return CheckConstraint(f"{column} BETWEEN 0 AND 1", name=f"{column}_between_zero_and_one")


def _ranked(table: str, parent: str, *, marked: bool) -> Index:
    """Keep the position of an element unique under its parent, those marked deleted apart."""
    return Index(
        f"uq_{table}_position",
        parent,
        "position",
        unique=True,
        postgresql_where=text("deleted_at IS NULL") if marked else None,
    )


class Stamped(Base):
    """The columns of audit of a row that changes (WF-DAT-0070), without a counter of its own.

    An author is an account, or the platform when null: the loader of the witness. Abstract: each
    table that has them declares them as its own.
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


class Audited(Stamped):
    """The columns of audit and the counter of the writes of a row written on its own."""

    __abstract__ = True

    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")


class Project(Audited):
    """A project: its attributes (WF-PRJ-0080), its state, its reference and current revisions.

    The list of its contributors and its work breakdown are written whole, each under a counter of
    its own, which a change of the project leaves as it is (``ContributorList``, ``WorkBreakdown``).
    """

    __tablename__ = "project"
    __table_args__ = (
        *bounded("label", LABEL_LENGTH),
        *bounded("code", CODE_LENGTH),
        # The one separator of the element of the ERP that bears it (WF-CRE-0020).
        CheckConstraint("code !~ '/'", name="code_without_slash"),
        *bounded("client", LABEL_LENGTH),
        CheckConstraint(_in("state", STATES), name="state_known"),
        _ratio("inflation_rate"),
        _ratio("win_probability"),
        counted(),
        CheckConstraint(
            "contributors_lock_version >= 0", name="contributors_lock_version_not_negative"
        ),
        CheckConstraint(
            "work_breakdown_lock_version >= 0", name="work_breakdown_lock_version_not_negative"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    # Null until it is entered; unique in the installation, nulls apart (WF-PRJ-0010).
    code: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    client: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    state: Mapped[str] = mapped_column(Text)
    inflation_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    win_probability: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    order_received_on: Mapped[date | None] = mapped_column(Date)
    reference_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("revision.id", ondelete="RESTRICT", use_alter=True), index=True
    )
    # Null when the project has no current revision (WF-REV-0010).
    current_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("revision.id", ondelete="RESTRICT", use_alter=True), index=True
    )
    contributors_lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    work_breakdown_lock_version: Mapped[int] = mapped_column(Integer, server_default="0")


class ProjectStateTransition(Base):
    """A transition of the state of a project, never changed nor deleted (WF-CYC-0130).

    Its author is an account, or the platform when null — an automatic transition, which has no
    reason; the first, at the creation, comes from no state.
    """

    __tablename__ = "project_state_transition"
    __table_args__ = (
        CheckConstraint(_in("from_state", STATES), name="from_state_known"),
        CheckConstraint(_in("to_state", STATES), name="to_state_known"),
        Index(None, "project_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey(Project.id, ondelete="RESTRICT"))
    from_state: Mapped[str | None] = mapped_column(Text)
    to_state: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column(Text)


class Contributor(Base):
    """An account inscribed on a project, with its kind (WF-PRJ-0060): an association.

    Added, changed in its kind or removed with the whole list, under the counter of the project.
    """

    __tablename__ = "contributor"
    __table_args__ = (CheckConstraint(_in("kind", CONTRIBUTOR_KINDS), name="kind_known"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey(Project.id, ondelete="RESTRICT"), primary_key=True
    )
    user_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    kind: Mapped[str] = mapped_column(Text)


class Subproject(Audited):
    """A subproject, by the code the ERP knows it by, unique in its project (WF-PRJ-0050).

    Its code names a tab of the workbook of the remaining commitments: no character a tab refuses
    (the form, here); the two names Waterfall gives its own tabs are refused by the service, which
    compares them normalised (#1502). Deleted for good while nothing cites it.
    """

    __tablename__ = "subproject"
    __table_args__ = (
        UniqueConstraint("project_id", "code"),
        *bounded("code", SUBPROJECT_CODE_LENGTH),
        CheckConstraint(f"code !~ '{TAB_FORBIDDEN}'", name="code_form"),
        *bounded("label", LABEL_LENGTH),
        counted(),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey(Project.id, ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))


class WorkPackage(Stamped):
    """A work package, level 1 of the work breakdown (WF-PRJ-0020), in the order of its position.

    Marked deleted (``deleted_at``) when a task of a marked revision bears it (EP-06), deleted for
    good otherwise; the work breakdown is written whole, under the counter of the project.
    """

    __tablename__ = "work_package"
    __table_args__ = (
        *bounded("label", LABEL_LENGTH),
        CheckConstraint("position >= 0", name="position_not_negative"),
        _ranked("work_package", "project_id", marked=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey(Project.id, ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    position: Mapped[int] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class OrderItem(Stamped):
    """An order item of a work package, level 2 of the work breakdown, marked deleted likewise."""

    __tablename__ = "order_item"
    __table_args__ = (
        *bounded("label", LABEL_LENGTH),
        CheckConstraint("position >= 0", name="position_not_negative"),
        _ranked("order_item", "work_package_id", marked=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey(Project.id, ondelete="RESTRICT"), index=True
    )
    work_package_id: Mapped[UUID] = mapped_column(ForeignKey(WorkPackage.id, ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    position: Mapped[int] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class Deliverable(Stamped):
    """A deliverable of an order item, level 3 of the work breakdown; deleted for good."""

    __tablename__ = "deliverable"
    __table_args__ = (
        *bounded("label", LABEL_LENGTH),
        CheckConstraint("position >= 0", name="position_not_negative"),
        _ranked("deliverable", "order_item_id", marked=False),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey(Project.id, ondelete="RESTRICT"), index=True
    )
    order_item_id: Mapped[UUID] = mapped_column(ForeignKey(OrderItem.id, ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    position: Mapped[int] = mapped_column(Integer)
