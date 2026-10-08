# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the examples the generators write say their figures, and the envelope they carry them in.

The summary of an example is French, as the contract is: a day, a count and an amount are
written as French writes them. The envelope is the Example object of OpenAPI, its description
saying that the example is generated and is not edited by hand.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, cast

from wftools import REPOSITORY

if TYPE_CHECKING:
    from decimal import Decimal

    from wftools.mockstructure import JsonObject, JsonValue

CORE_ONLY = "Lu sur le seul cœur du témoin, jusqu'à EP-02/L45 (#528)."
"""What an example read on the core alone says of itself, until EP-02/L45 reads the whole
structure (#376): its figures are not those of the thousand tasks that carry the core."""


def _default_limit() -> int:
    """Return the default of the parameter `Limit` of the contract: one page of a list."""
    text = (REPOSITORY / "docs/api/components/parameters.yaml").read_text(encoding="utf-8")
    found = re.search(r"^Limit:\n(?:[ \t].*\n)*?.*default:\s*(\d+)", text, re.MULTILINE)
    if found is None:
        message = "the parameter Limit of the contract has no default"
        raise ValueError(message)
    return int(found.group(1))


PAGE = _default_limit()
"""The page of a list when none is asked: the default of `Limit`, read from the contract."""

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


def example(summary: str, value: JsonValue) -> JsonObject:
    """Return an example of the contract: its summary, its description, its value."""
    return {"summary": summary, "description": DESCRIPTION, "value": value}
