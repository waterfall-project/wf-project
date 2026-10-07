# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the examples the generators write say their figures, and the envelope they carry them in.

The summary of an example is French, as the contract is: a day, a count and an amount are
written as French writes them. The envelope is the Example object of OpenAPI, its description
saying that the example is generated and is not edited by hand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from wftools.mockstructure import JsonObject, JsonValue

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


def example(summary: str, value: JsonValue) -> JsonObject:
    """Return an example of the contract: its summary, its description, its value."""
    return {"summary": summary, "description": DESCRIPTION, "value": value}
