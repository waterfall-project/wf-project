# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cost categories, the hourly rates and their grid, as the fake back serves them.

The categories (WF-REF-0010) and the rates with their grid (WF-REF-0060).

Split from ``wftools.mockdata`` with ``wftools.mockvolumes``, to keep it under the nine hundred
lines (US-2520): the volumes read the categories and the grid, and ``mockdata`` writes the
volumes, so that the two could not import each other.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcategories, mockhistory
from wftools.mockstructure import (
    COMMISSIONING_RATE,
    ELECTRICAL_RATE,
    LABOR,
    JsonObject,
    JsonValue,
    draw,
    hourly_rate,
    money,
)
from wftools.mockwitness import COMMISSIONING, ELECTRICAL_ENGINEERING, INSTALLED

if TYPE_CHECKING:
    from collections.abc import Iterable

RATE_YEARS = range(2012, 2027)
"""Fifteen years of rates, up to the reference year of the witness estimate."""

USER = "01926f3a-7c00-7000-8000-000000000301"

_AUDIT: JsonObject = {
    "created_at": mockhistory.stamp(INSTALLED.instant),
    "created_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
    "updated_at": mockhistory.stamp(INSTALLED.instant),
    "updated_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
}

_INSTALLED_AUDIT: JsonObject = {
    "created_at": mockhistory.stamp(INSTALLED.instant),
    "created_by": {"kind": "platform"},
    "updated_at": mockhistory.stamp(INSTALLED.instant),
    "updated_by": {"kind": "platform"},
}
"""The audit of what the installation itself creates: the provision for risks, its nature and the
default calendar, written by the platform at its bootstrap, not by an account."""


# --- The grid of hourly rates -------------------------------------------------------------


def categories() -> list[JsonValue]:
    """Return the answer of listCostCategories: the labour categories first, then the others."""
    return [
        category
        for entries, code, account, nature in mockcategories.groups()
        for category in categories_of(entries, code, account, nature)
    ]


def categories_of(
    entries: Iterable[tuple[str, str]], code: str, account: str, nature: JsonObject
) -> list[JsonValue]:
    """Return the categories of a nature, each with its nature resolved at the reading.

    Its label, its kind, and whether it is active (`cost_type_is_active`); a category of a
    deactivated nature is deactivated with it (WF-REF-0010; EP-14/L42s, C-291).
    """
    return [
        {
            "cost_category_id": category,
            "code": f"{code}-{rank:03d}",
            "label": label,
            "cost_type_id": nature["cost_type_id"],
            "cost_type_label": nature["label"],
            "cost_type_kind": nature["kind"],
            "cost_type_is_active": nature["is_active"],
            "accounting_code": f"{account}{rank:03d}",
            "is_active": nature["is_active"],
            "audit": _INSTALLED_AUDIT if nature["kind"] == "provision" else _AUDIT,
            "lock_version": 1,
        }
        for rank, (category, label) in enumerate(entries, start=1)
    ]


def hourly_rates() -> list[JsonValue]:
    """Return the answer of listHourlyRates: the years of rates of the electrical engineering."""
    return [_rate(ELECTRICAL_ENGINEERING, ELECTRICAL_RATE, year) for year in RATE_YEARS]


def _rate(category: str, last_amount: Decimal, year: int) -> JsonObject:
    """Return the rate of a category for a year, grown by the step each year up to the last."""
    return {
        "cost_category_id": category,
        "year": year,
        "amount": money(hourly_rate(last_amount, year)),
        "audit": _AUDIT,
        "lock_version": 1,
    }


_EMPTY_YEARS = 4
"""How many of the first years a category may leave without a rate: an empty cell of the grid."""


def hourly_rate_grid() -> JsonObject:
    """Return the answer of getHourlyRateGrid: the labour categories in rows, the years in columns.

    The two categories the estimate employs carry their fifteen years — the electrical
    engineering those of ``listHourlyRates`` —; each other category draws its rate of the
    reference year, and the first years it left without a rate (WF-REF-0060).
    """
    known = {ELECTRICAL_ENGINEERING: ELECTRICAL_RATE, COMMISSIONING: COMMISSIONING_RATE}
    rows: list[JsonValue] = []
    for entry in categories():
        category = cast("JsonObject", entry)
        if category["cost_type_id"] != LABOR:
            continue
        identifier_ = str(category["cost_category_id"])
        last = known.get(identifier_)
        if last is None:
            last = Decimal(draw(f"rate/{identifier_}", 4_000, 12_000)) / 100
        first = RATE_YEARS[0] + (
            0 if identifier_ in known else draw(f"first-year/{identifier_}", 0, _EMPTY_YEARS)
        )
        rows.append(
            {
                "cost_category_id": identifier_,
                "code": category["code"],
                "label": category["label"],
                "is_active": True,
                "cells": [
                    _rate(identifier_, last, year) if year >= first else None for year in RATE_YEARS
                ],
            }
        )
    return {"years": list(RATE_YEARS), "rows": rows}
