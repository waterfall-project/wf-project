# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summary tasks of a revision (WF-IND-0030, WF-IND-0060; US-1680).

For each summary task asked for, the share of the budgeted amounts of its subtree — its own lines
included, provisions excluded — its completed tasks carry, to four decimals, whatever the state of
the project; none when that total is nought (``no_budgeted_amount``). The planning answers it in
the facet of a task through its registry ``register_physical_progress``, which US-1680 declares and
fills with this function (EP-10, "L'avancement physique").

Declared by US-1660/L1, the socle of EP-10.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


def physical_progress(
    session: Session, revision_id: UUID, node_ids: Collection[UUID]
) -> Mapping[UUID, Decimal | None]:
    """Give the physical progress of each summary task asked for, none without budgeted amount."""
    msg = "physical_progress is filled by US-1680"
    raise NotImplementedError(msg)
