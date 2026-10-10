# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the roles and of the catalogue, private to the module (§4.4.1, regime "platform").

The catalogue is written by the migrations alone (WF-ADM-0100): the service only reads it. A role
is never deleted: it is marked deleted, and its row stays for what cites it (WF-DAT-0080). The two
associations hold their two keys and nothing else: they lose their rows one by one.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime

KINDS = ("function_read", "function_write", "irreversible", "structuring")

# The collation of a label: a sort compares the code points, accents and case included.
CODE_POINTS = "C"

# A table the migrations fill and the service only reads: the tests do not empty it.
WRITTEN_BY_MIGRATION = "written_by_migration"


class Permission(Base):
    """A permission of the catalogue: one function read or written, or an action of its own."""

    __tablename__ = "permission"
    __table_args__ = (
        CheckConstraint(f"kind IN ({', '.join(repr(kind) for kind in KINDS)})", name="kind_known"),
        CheckConstraint(
            "(fbs_code IS NULL) = (kind IN ('irreversible', 'structuring'))",
            name="fbs_code_of_a_function",
        ),
        CheckConstraint("fbs_code ~ '^FBS-[0-9]+\\.[0-9]+$'", name="fbs_code_form"),
        CheckConstraint("position >= 0", name="position_not_negative"),
        {"info": {WRITTEN_BY_MIGRATION: True}},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    kind: Mapped[str] = mapped_column(Text)
    fbs_code: Mapped[str | None] = mapped_column(Text)
    # The order of the catalogue, that of the contract: the lines of the matrix follow it.
    position: Mapped[int] = mapped_column(SmallInteger, unique=True)


class AccessRole(Base):
    """A named set of permissions; deleted, it is no longer read nor given (WF-ADM-0090)."""

    __tablename__ = "access_role"
    __table_args__ = (
        CheckConstraint("char_length(label) BETWEEN 1 AND 100", name="label_length"),
        CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(Text(collation=CODE_POINTS))
    is_predefined: Mapped[bool]
    # Null while the role lives; the moment of its deletion after.
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )


class AccessRolePermission(Base):
    """A permission a role grants."""

    __tablename__ = "access_role_permission"

    access_role_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_role.id", ondelete="RESTRICT"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permission.id", ondelete="RESTRICT"), primary_key=True
    )


class UserAccessRole(Base):
    """A role an account holds."""

    __tablename__ = "user_access_role"

    user_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"), primary_key=True
    )
    # The holders of a role are counted and looked for by the role.
    access_role_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_role.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
