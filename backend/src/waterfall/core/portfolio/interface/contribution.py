# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a project gives the portfolio, by revision (EP-11, "La contribution d'un projet").

At the marking, ``store_contribution`` keeps, by ``keep_document`` of the indicators, the documents
of the kinds the state of the project calls for: a project In progress the workload, the cost
structure, the risks and the milestones; an offer the same but what asks for a reference, and its
curves. An exception reaches the marking, which fails whole (the policy of EP-10). Registered at
``register_indicators`` of the revisions, after ``store_indicators``, at the import of this
interface (US-2680/L2). On the current day, the same computation gives the same documents for the
current revision of the project, kept by the cache of the indicators under the fingerprint of the
project.

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L2, the risks by US-2680/L3.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def store_contribution(session: Session, revision_id: UUID, act: Act) -> None:
    """Keep the documents of the portfolio of a revision, in the transaction of its marking."""
    msg = "store_contribution is filled by US-2680/L2"
    raise NotImplementedError(msg)
