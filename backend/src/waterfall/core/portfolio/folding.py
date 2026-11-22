# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The search of the list, compared as every search of the contract is (US-2690).

The list is filtered in memory, on the rows formed; its texts — the label, the code — are compared
by the database, as any search is: ignoring case and accents, as PostgreSQL's ``unaccent`` writes
them (README of the contract, "A search…"). One statement for all the texts: they are sent as one
array, and the answer says, for each, whether it holds the text searched.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Text, func, literal, select

from waterfall.platform.database import contains

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session


def holding(session: Session, texts: Sequence[str], searched: str) -> list[bool]:
    """Tell, for each text, whether it contains the text searched, whatever its case and accents.

    In the order of ``texts``; no statement for none.
    """
    if not texts:
        return []
    unnested = (
        func.unnest(literal(list(texts), ARRAY(Text)))
        .table_valued("text", with_ordinality="rank")
        .render_derived()
    )
    found = select(contains(unnested.c.text, searched)).order_by(unnested.c.rank)
    return list(session.scalars(found))
