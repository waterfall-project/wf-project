# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference a load of lines reads, read once for all its lines (US-1570/L2).

A line created is judged and priced on what it names — its role, its category, its subproject, the
basis of its revision, the rate of its category, the calendar of its role —, each read by a
statement of its own (``entries``, ``writing``). The witness creates some five thousand lines a
revision, on a few dozen roles and categories: read for each line, those statements, with a flush
of each line, made the loading of the lines two thirds of that of the witness (#2716).

``remembering`` opens, for the load of the lines of one revision (``loading``), a memory of those
reads in the session; ``recalled`` reads each once while it is open, and every time otherwise: the
API, which writes a line at a time, reads afresh as it did. The load writes none of what is
remembered — the reference, the project and its rates stay as they are while its lines are
written —, so what is recalled is what a statement would read.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Hashable

    from sqlalchemy.orm import Session

_MEMORY = "waterfall.estimate.recalling"


@contextmanager
def remembering(session: Session) -> Generator[None]:
    """Remember, until the block ends, what ``recalled`` reads in the session."""
    session.info[_MEMORY] = {}
    try:
        yield
    finally:
        del session.info[_MEMORY]


def remembers(session: Session) -> bool:
    """Tell whether a load of lines is under way: its lines are then flushed together."""
    return _MEMORY in session.info


def recalled[T](session: Session, key: Hashable, read: Callable[[], T]) -> T:
    """Give what ``read`` reads, once under ``remembering`` for each key; every time otherwise."""
    memory = cast("dict[Hashable, object] | None", session.info.get(_MEMORY))
    if memory is None:
        return read()
    if key not in memory:
        memory[key] = read()
    return cast("T", memory[key])
