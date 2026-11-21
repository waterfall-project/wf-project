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

# What opens a list of tables in a statement: a keyword, which ``FROM`` may follow with several.
_OPENS = re.compile(r"\b(FROM|JOIN|INTO|UPDATE)\s+", re.IGNORECASE)
# One table of the list: quoted or not, with the schema it may carry, then its alias, if any.
_TABLE = re.compile(r'(?:ONLY\s+)?(?:"?\w+"?\.)?"?(\w+)"?(?:\s+(?:AS\s+)?\w+)?', re.IGNORECASE)
# The words that end a table where an alias could stand: they are keywords, not aliases.
_KEYWORDS = frozenset(
    {"on", "using", "where", "group", "order", "limit", "join", "left", "right", "inner", "full"}
    | {"cross", "set", "values", "returning", "having", "union"}
)
_COMMA = re.compile(r"\s*,\s*")


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
    """Name the tables a statement reads or writes, each one of a ``FROM a, b`` list included."""
    found: set[str] = set()
    for opening in _OPENS.finditer(statement):
        at = opening.end()
        while named := _TABLE.match(statement, at):
            found.add(named.group(1).lower())
            at = named.end()
            # An alias the pattern took may be the keyword that follows the table: step back.
            tail = statement[named.end(1) : named.end()].split()
            if tail and tail[-1].lower() in _KEYWORDS:
                at = named.end() - len(tail[-1])
            if not (comma := _COMMA.match(statement, at)):
                break
            at = comma.end()
    return found


def touching(statements: Iterable[str], tables: Iterable[str]) -> list[str]:
    """Give the statements that read or write one of the tables."""
    wanted = {name.lower() for name in tables}
    return [each for each in statements if tables_of(each) & wanted]
