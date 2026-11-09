# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the lines of an estimate tell the cost settings, private to the module (EP-07).

One registry, ``cost_settings.employment``, filled by the estimate at the import of its interface,
which this module never imports (EP-07, "Les points d'extension"): each entry tells, of the
categories given, those a line employs — which a change of the kind of a nature or of a category
refuses (WF-REF-0030, WF-REF-0040) —, and prices again the current revisions a rate of the reference
just written changes (``RateWritten``, ``setHourlyRate``; EP-07, "Le calcul des montants").

Held here, not in the file of the categories, so that the rates, which the categories read, call it
without the two files importing each other. The interface offers it by the file of the categories
(``register_employment``, ``category_is_employed``).

Declared by US-1490/L1; the rates written by US-1500/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RateWritten:
    """A rate of the reference just set or corrected: its category, its year, and the instant."""

    cost_category_id: UUID
    year: int
    at: datetime


def no_price_follows(session: Session, written: RateWritten) -> None:
    """Price nothing again: what an entry that only tells the categories employed answers."""
    del session, written


type Employed = Callable[[Session, Collection[UUID]], frozenset[UUID]]
type Repriced = Callable[[Session, RateWritten], None]

# What tells, of the categories given, those a line employs, and what prices again the revisions a
# rate written changes: the estimate's (EP-07), each entry the pair.
_EMPLOYMENTS: Registry[tuple[Employed, Repriced]] = Registry("cost_settings.employment")


def register_employment(
    employed: Employed, repriced: Repriced = no_price_follows
) -> Callable[[], None]:
    """Add what tells the categories a line employs, and what a rate written prices again.

    ``repriced`` is given the transaction of the rate written, under the lock of the natures, which
    it holds until the end: it locks what it prices after it. Give the withdrawal of the pair.
    """
    return _EMPLOYMENTS.register((employed, repriced))


def category_is_employed(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a line of a quote employs (WF-REF-0030, WF-REF-0040).

    Those each registered answer names (``register_employment``): none while nothing is
    registered, before EP-07 fills it.
    """
    employed: set[UUID] = set()
    for answer, _ in _EMPLOYMENTS.entries():
        employed |= answer(session, category_ids)
    return frozenset(employed)


def price_after_rate(session: Session, written: RateWritten) -> None:
    """Have each entry registered price again what a rate of the reference just written changes."""
    for _, repriced in _EMPLOYMENTS.entries():
        repriced(session, written)
