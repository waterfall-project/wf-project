# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Identifiers of the rows: UUID version 7, drawn by the service and never by the database.

A version 7 identifier starts with the time it was drawn at, so the rows sort in the order they
were created; it is random for the rest, so two instances of the service drawing at the same
instant do not produce the same one (WF-DAT-0060). Python 3.14 has ``uuid.uuid7``, but the
service draws with ``uuid_utils``.

The loader of the witness draws its own, in order (``drawn_in_order``; EP-08, US-2650/L1): every
identifier a module draws while it loads — those no example of the contract names, which the
witness does not impose — is the next of a count, under a fixed instant, so that two loadings of
the witness give the same identifiers, in the order the rows are written (WF-QUA-0040). A
version 7 identifier still, which sorts before any the service draws afterwards.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from itertools import count
from typing import TYPE_CHECKING
from uuid import UUID

import uuid_utils

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from datetime import datetime

# The counter the identifiers are drawn from while a loader holds it; none otherwise.
_DRAWN: ContextVar[Iterator[int] | None] = ContextVar("identifiers_drawn", default=None)
# The instant, in milliseconds, the identifiers of that count bear.
_EPOCH: ContextVar[int] = ContextVar("identifiers_epoch", default=0)
# The layout of a version 7 identifier (RFC 9562): 48 bits of milliseconds, the version, 12 bits,
# the variant, 62 bits. The count fills the last 62, the 12 before it stay nought.
_VERSION_7 = 0x7 << 76
_VARIANT = 0b10 << 62
_COUNT_BITS = 62


def new_id() -> UUID:
    """Draw a new identifier: the next of the count a loader holds, else at random."""
    drawn = _DRAWN.get()
    if drawn is not None:
        return ordered_identifier(_EPOCH.get(), next(drawn))
    return UUID(bytes=uuid_utils.uuid7().bytes)


def ordered_identifier(milliseconds: int, number: int) -> UUID:
    """Give the version 7 identifier of an instant, in milliseconds, and of a number in its count.

    The same two give the same identifier; a greater number, at the same instant, a greater one.
    """
    if not 0 <= number < 1 << _COUNT_BITS:
        message = f"the number {number} does not fit an identifier"
        raise ValueError(message)
    return UUID(int=(milliseconds << 80) | _VERSION_7 | _VARIANT | number)


@contextmanager
def drawn_in_order(at: datetime) -> Generator[None]:
    """Draw every identifier asked in the block in order, from 1, under the instant ``at``.

    For the loader of the witness, whose identifiers two loadings must give alike (WF-QUA-0040).
    The block restores the drawing at random when it ends.
    """
    drawn, epoch = _DRAWN.set(count(1)), _EPOCH.set(int(at.timestamp() * 1000))
    try:
        yield
    finally:
        _EPOCH.reset(epoch)
        _DRAWN.reset(drawn)


def read_identifier(text: str) -> UUID | None:
    """Read an identifier as the contract writes it (``format: uuid``); none for any other form.

    The hyphenated form, in either case. ``UUID`` also reads braces, ``urn:uuid:`` and no hyphen at
    all: those are no identifier of the contract, and name nothing.
    """
    try:
        found = UUID(text)
    except ValueError:
        return None
    return found if str(found) == text.lower() else None
