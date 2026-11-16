# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a revision keeps of its indicators at its marking (WF-DAT-0040; US-1670/L1).

``store_indicators`` is the entry of the indicators in ``register_indicators`` of the revisions:
called in the transaction of the marking, after what the estimate keeps and before the revision is
written, it writes the documents of the revision — the estimate and the remaining to commit for the
project, each subproject and ``unassigned``, and, the project In progress, its indicators and its
three curves —, each computed at the instant of the marking (``act.at``), its author the requester
(EP-10, "La conservation au marquage"). Nothing is caught: a computation that raises fails the
marking, nothing being written.

Registered by US-1660/L1, the socle of EP-10, without effect: a marking keeps nothing until
US-1670/L1 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def store_indicators(session: Session, revision_id: UUID, act: Act) -> None:
    """Keep the indicators of a revision being marked: none until US-1670/L1."""
    del session, revision_id, act
