# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the accounts, private to the module (§4.4.1, regime "platform").

An account is never deleted: its state says whether it may sign in. Its address does not
identify it for the rest of the database, its identifier does: every row that refers to an
account holds the identifier, so changing the address changes nothing else (WF-DAT-0060).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime
from waterfall.platform.installation import AVATAR_MAX_BYTES

ORIGINS = ("local", "directory", "identity_provider")
STATES = ("active", "deactivated")
AVATAR_MEDIA_TYPES = ("image/png", "image/jpeg")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class UserAccount(Base):
    """A person who may sign in to the platform."""

    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint("char_length(last_name) BETWEEN 1 AND 100", name="last_name_length"),
        CheckConstraint("char_length(first_name) BETWEEN 1 AND 100", name="first_name_length"),
        CheckConstraint("char_length(email) >= 1", name="email_not_empty"),
        CheckConstraint("char_length(idp_subject) >= 1", name="idp_subject_not_empty"),
        CheckConstraint(_in("origin", ORIGINS), name="origin_known"),
        CheckConstraint(_in("state", STATES), name="state_known"),
        CheckConstraint(
            _in("avatar_media_type", AVATAR_MEDIA_TYPES), name="avatar_media_type_known"
        ),
        CheckConstraint(
            f"octet_length(avatar) BETWEEN 1 AND {AVATAR_MAX_BYTES}", name="avatar_size"
        ),
        CheckConstraint(
            "(avatar IS NULL) = (avatar_media_type IS NULL)", name="avatar_with_its_media_type"
        ),
        CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
        # One address per person, whatever its case (WF-ADM-0050), declared here and not
        # left to a rule of the services.
        Index("uq_user_account_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    last_name: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    idp_subject: Mapped[str] = mapped_column(Text, unique=True)
    origin: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, server_default="active")
    display_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    # Read only when asked for: up to 8 MiB that reading an account does not need.
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    avatar_media_type: Mapped[str | None] = mapped_column(Text)
    lock_version: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
