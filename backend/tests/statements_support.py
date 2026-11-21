# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests that watch the statements of the database share: hear them, and name the tables.

A test that says what a read does not touch hears the statements an engine sends while a block
runs, then names the tables a statement reads. The tables are those of the ``FROM`` and ``JOIN``
clauses, and of the ``INSERT``, ``UPDATE`` and ``DELETE`` ones, read as the driver sends them.
"""

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import event

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from sqlalchemy import Engine

# What names a table in a statement: after a keyword, quoted or not, and the schema it may carry.
_AFTER = re.compile(
    r'\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:ONLY\s+)?(?:"?\w+"?\.)?"?(\w+)"?', re.IGNORECASE
)


@contextmanager
def heard(engine: Engine) -> Generator[list[str]]:
    """Collect the statements the engine sends while the block runs, in the order it sends them."""
    sent: list[str] = []

    def hear(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    event.listen(engine, "before_cursor_execute", hear)
    try:
        yield sent
    finally:
        event.remove(engine, "before_cursor_execute", hear)


def tables_of(statement: str) -> set[str]:
    """Name the tables a statement reads or writes."""
    return {name.lower() for name in _AFTER.findall(statement)}


def touching(statements: Iterable[str], tables: Iterable[str]) -> list[str]:
    """Give the statements that read or write one of the tables."""
    wanted = {name.lower() for name in tables}
    return [each for each in statements if tables_of(each) & wanted]
