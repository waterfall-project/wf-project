# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates of the categories of labour, by year.

The grid, the rates of a category, one rate set (WF-REF-0050, 0060).

Empty until US-0830 fills it, but for the question the categories ask (``category_is_rated``).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def category_is_rated(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those that bear a rate, whatever its year (WF-REF-0030).

    A nature whose category bears one, and a category that bears one, keep their kind (WF-REF-0050).
    No rate can be set before US-0830 serves them: none is yet, which it replaces.
    """
    del session, category_ids
    return frozenset()
