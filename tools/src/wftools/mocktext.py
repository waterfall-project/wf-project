# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the examples the generators write say their figures, and the envelope they carry them in.

The summary of an example is French, as the contract is: a day, a count and an amount are
written as French writes them. The envelope is the Example object of OpenAPI, its description
saying that the example is generated and is not edited by hand. A searched text is compared as
the service will compare it, through the table PostgreSQL ships with ``unaccent``, then lowered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, cast

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal

    from wftools.mockstructure import JsonObject, JsonValue

CORE_ONLY = "Lu sur le seul cœur du témoin, jusqu'à EP-02/L45 (#528)."
"""What an example read on the core alone says of itself, until EP-02/L45 reads the whole
structure (#376): its figures are not those of the thousand tasks that carry the core."""


def _limit(key: str) -> int:
    """Return a bound of the parameter `Limit` of the contract: its default, or its maximum."""
    text = (REPOSITORY / "docs/api/components/parameters.yaml").read_text(encoding="utf-8")
    found = re.search(rf"^Limit:\n(?:[ \t].*\n)*?.*\b{key}:\s*(\d+)", text, re.MULTILINE)
    if found is None:
        message = f"the parameter Limit of the contract has no {key}"
        raise ValueError(message)
    return int(found.group(1))


PAGE = _limit("default")
"""The page of a list when none is asked: the default of `Limit`, read from the contract."""

MAX_LIMIT = _limit("maximum")
"""The largest page the contract takes: the maximum of `Limit`, read from the contract."""

DESCRIPTION = "Exemple engendré par `make mock-data` (`wftools.mockdata`) : il ne se retouche pas."

_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def day(value: date) -> str:
    """Write a day as French does: 3 juin 2026, 1er février 2027."""
    number = "1er" if value.day == 1 else str(value.day)
    return f"{number} {_MONTHS[value.month - 1]} {value.year}"


def count(value: int) -> str:
    """Write a count as French does: thousands apart by a narrow no-break space."""
    return f"{value:,}".replace(",", "\u202f")


def amount(value: Decimal, places: int = 2) -> str:
    """Write an amount as French does: 60 553 621,36."""
    return f"{value:,.{places}f}".replace(",", "\u202f").replace(".", ",")


def listed(items: list[str]) -> str:
    """Write a list as French does: A, B et C; nothing for no item."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " et " + items[-1]


def float_said(task: JsonObject) -> str:
    """Say where a task stands to the critical path, from its float as the reading gives it."""
    if task.get("is_critical") is True:
        return "sur le chemin critique"
    total = cast("dict[str, str]", task["total_float"])
    return f"avec {total['value'].replace('.', ',')} jours ouvrés de marge"


def span(task: JsonObject) -> str:
    """Say the dates of a task: du 1er juillet 2026 au 18 décembre 2026."""
    start, finish = (cast("dict[str, str]", task[key])["date"] for key in ("start", "finish"))
    return f"du {day(date.fromisoformat(start))} au {day(date.fromisoformat(finish))}"


@dataclass(frozen=True, slots=True)
class Unaccent:
    """A table of PostgreSQL's ``unaccent``: what each source becomes, and the longest source."""

    rules: Mapping[str, str]
    longest: int

    @classmethod
    def read(cls, text: str) -> Unaccent:
        """Read a table as ``unaccent`` reads its rules file.

        A line is a source, then its translation, apart by blanks; a source alone is dropped,
        as ``unaccent`` drops it. A line that starts with « # » is the header of the copy,
        which PostgreSQL does not read. A line of more than two strings is refused: ``unaccent``
        would skip it, and a copy that differs from the shipped table must not go unseen.
        """
        rules: dict[str, str] = {}
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            source, *translation = line.split()
            if len(translation) > 1:
                message = f"an unaccent rule has more than two strings: {line!r}"
                raise ValueError(message)
            rules[source] = "".join(translation)
        return cls(rules, max(map(len, rules), default=0))

    def __call__(self, text: str) -> str:
        """Return a text as ``unaccent`` returns it with this table.

        From left to right, the longest source of the table that starts at a character is
        replaced by its translation; a character that starts none stays itself, accented or not.
        """
        written: list[str] = []
        start = 0
        while start < len(text):
            for size in range(min(self.longest, len(text) - start), 0, -1):
                source = text[start : start + size]
                if source in self.rules:
                    written.append(self.rules[source])
                    start += size
                    break
            else:
                written.append(text[start])
                start += 1
        return "".join(written)


UNACCENT = Unaccent.read(Path(__file__).with_name("unaccent.rules").read_text(encoding="utf-8"))
"""The table PostgreSQL ships with ``unaccent``, versioned with its licence (``unaccent.rules``):
« é » becomes « e », « œ » « oe », « ß » « ss », « ø » « o »."""


def folded(text: str) -> str:
    """Return a text as a search compares it: transliterated as ``unaccent`` does, then lowered.

    The rule of every search of the contract (docs/api/README.md, « Une recherche… »), decided by
    the author on 2026-10-09: the table PostgreSQL ships, then ``lower()``, as the service will
    search by ``lower(unaccent(…))`` (EP-03). « Études » reads « etudes », « Main-d'œuvre »
    « main-d'oeuvre », « Straße » « strasse » and « Søren » « soren ».
    """
    return UNACCENT(text).lower()


def holds(value: str, text: str) -> bool:
    """Whether a text of the universe holds a searched text, as every search of the contract."""
    return folded(text) in folded(value)


def example(summary: str, value: JsonValue) -> JsonObject:
    """Return an example of the contract: its summary, its description, its value."""
    return {"summary": summary, "description": DESCRIPTION, "value": value}
