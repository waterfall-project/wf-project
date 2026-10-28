# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cost categories of the universe, grouped by nature (§4.6.2, #792).

``wftools.mockdata`` writes them in ``fixtures/api/volume/cost_categories.json``. What the other
examples say of a category — the flag a risk carries of its category, ``wftools.mockhistory`` —
is read here, from the generator in memory, never from that file, which the same ``make
mock-data`` writes: a run reads nothing the previous run left, and two runs in a row give the same
examples.
"""

from __future__ import annotations

from functools import cache

from wftools.mockids import CATEGORIES, identifier
from wftools.mockstructure import (
    CATEGORY_LABELS,
    LABOR,
    NON_LABOR,
    PROVISION,
    JsonObject,
)
from wftools.mockwitness import (
    COMMISSIONING,
    ELECTRICAL_ENGINEERING,
    EQUIPMENT,
    PROVISIONS,
    SUBCONTRACTING,
    fixture,
)

LABOR_CATEGORY_COUNT = 150
CATEGORY_COUNT = 200

_TRADES = (
    "Ingénierie mécanique",
    "Automatisme",
    "Électricité",
    "Instrumentation",
    "Génie civil",
    "Tuyauterie",
    "Chaudronnerie",
    "Informatique industrielle",
    "Qualité",
    "Méthodes",
)
_PURCHASES = (
    "Matériel mécanique",
    "Câbles",
    "Instruments",
    "Location d'engins",
    "Transport",
    "Essais en laboratoire",
    "Études externes",
)

type Group = tuple[list[tuple[str, str]], str, str, JsonObject]
"""A nature's categories — their identifier and label —, the code and the account they carry, and
the nature itself."""


@cache
def groups() -> list[Group]:
    """Return the categories by nature: labour first, then the others, then the provisions."""
    labor = [
        (ELECTRICAL_ENGINEERING, CATEGORY_LABELS[ELECTRICAL_ENGINEERING]),
        (COMMISSIONING, CATEGORY_LABELS[COMMISSIONING]),
    ]
    labor.extend(
        (identifier(CATEGORIES, n), f"{_TRADES[n % len(_TRADES)]} — niveau {n // len(_TRADES) + 1}")
        for n in range(LABOR_CATEGORY_COUNT - len(labor))
    )
    non_labor = [
        (SUBCONTRACTING, CATEGORY_LABELS[SUBCONTRACTING]),
        (EQUIPMENT, CATEGORY_LABELS[EQUIPMENT]),
    ]
    others = CATEGORY_COUNT - LABOR_CATEGORY_COUNT - 1
    non_labor.extend(
        (
            identifier(CATEGORIES, LABOR_CATEGORY_COUNT + n),
            f"{_PURCHASES[n % len(_PURCHASES)]} — lot {n // len(_PURCHASES) + 1}",
        )
        for n in range(others - len(non_labor))
    )
    # Each category names its nature, and its kind, as the natures of the universe do.
    natures = {nature["cost_type_id"]: nature for nature in fixture("cost_types")["items"]}
    return [
        (labor, "MO", "641", natures[LABOR]),
        (non_labor, "ACH", "604", natures[NON_LABOR]),
        ([(PROVISIONS, CATEGORY_LABELS[PROVISIONS])], "PRV", "681", natures[PROVISION]),
    ]


def nature_of(category: str) -> JsonObject:
    """Return the nature a category belongs to, as the generator groups it."""
    [nature] = [
        nature
        for entries, _, _, nature in groups()
        if category in {identifier_ for identifier_, _ in entries}
    ]
    return nature
