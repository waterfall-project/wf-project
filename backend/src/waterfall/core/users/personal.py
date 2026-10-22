# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the holder of an account sets alone: its preferences of display and its avatar.

Personal settings, cantoned to the presentation (WF-ADM-0040, WF-ADM-0080): each account changes
its own, and nobody those of another. They are no change of the account an administrator manages:
neither its version nor its audit columns move, and a form opened on the account stays valid, as
when its sessions are closed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from waterfall.core.users.accounts import lock_account
from waterfall.core.users.tables import UserAccount
from waterfall.platform.errors import FieldError, UnprocessableError

# The settings of each grid, by the name of the grid (WF-IHM-0060), and the layout of each
# timeline, by its identifier (WF-PLA-0140): tables whose entries a change replaces one by one.
TABLES = ("grids", "timelines")
# The entries a table holds at most, once a change applies as when it is sent (#874, #1235).
MOST_ENTRIES = 100
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
PNG = "image/png"
JPEG = "image/jpeg"
# The first bytes of each kind of image an avatar may be: its signature, whatever it is said to be.
SIGNATURES = {PNG: b"\x89PNG\r\n\x1a\n", JPEG: b"\xff\xd8\xff"}


def merged(current: Mapping[str, Any], sent: Mapping[str, Any]) -> dict[str, Any]:
    """Give the preferences once a change applies: only what it carries changes.

    In ``grids``, only the grids it names, each replaced whole; a grid sent ``None`` is forgotten,
    and finds its settings by default again. So in ``timelines``, by timeline (EP-15/US-0530).

    The preferences are read with the account at each request: a table grows by successive
    changes no further than one change may carry, a hundred entries, and a change that would take
    it past them is refused on the table, ``VALUE_TOO_LONG`` (#874, #1235). One that does not
    grow it — that forgets or replaces entries — is never refused for its size.
    """
    preferences = {**current, **{name: value for name, value in sent.items() if name not in TABLES}}
    faults: list[FieldError] = []
    for table in TABLES:
        if table in sent:
            before: dict[str, Any] = dict(current.get(table) or {})
            entries = dict(before)
            for name, entry in sent[table].items():
                if entry is None:
                    entries.pop(name, None)
                else:
                    entries[name] = entry
            if len(entries) > max(MOST_ENTRIES, len(before)):
                faults.append(FieldError(f"/{table}", VALUE_TOO_LONG))
            preferences[table] = entries
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return preferences


def change_preferences(session: Session, user_id: UUID, sent: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a change to the preferences of an account, and give them as they now are.

    The account is locked, then its preferences read under the lock: two changes at once, of two
    grids, each keep the other's, and their sum is bounded as each is (#1235).
    """
    account = lock_account(session, user_id)
    preferences = merged(account.display_preferences, sent)
    session.execute(
        update(UserAccount).where(UserAccount.id == user_id).values(display_preferences=preferences)
    )
    return preferences


def image_type(image: bytes) -> str | None:
    """Say what kind of image an avatar is by its content; ``None`` if neither PNG nor JPEG."""
    return next((kind for kind, first in SIGNATURES.items() if image.startswith(first)), None)


@dataclass(frozen=True, slots=True)
class Avatar:
    """The image of an account, and its type, read from its content when it was put."""

    image: bytes
    media_type: str


def put_avatar(session: Session, user_id: UUID, avatar: Avatar) -> None:
    """Give an account its avatar, or replace the one it had."""
    session.execute(
        update(UserAccount)
        .where(UserAccount.id == user_id)
        .values(avatar=avatar.image, avatar_media_type=avatar.media_type)
    )


def withdraw_avatar(session: Session, user_id: UUID) -> None:
    """Withdraw the avatar of an account, which shows its image by default again."""
    session.execute(
        update(UserAccount)
        .where(UserAccount.id == user_id)
        .values(avatar=None, avatar_media_type=None)
    )


def read_avatar(session: Session, user_id: UUID) -> Avatar | None:
    """Read the avatar of an account; ``None`` for an account without one, or no account."""
    row = session.execute(
        select(UserAccount.avatar, UserAccount.avatar_media_type).where(UserAccount.id == user_id)
    ).first()
    if row is None or row.avatar is None or row.avatar_media_type is None:
        return None
    return Avatar(row.avatar, row.avatar_media_type)
