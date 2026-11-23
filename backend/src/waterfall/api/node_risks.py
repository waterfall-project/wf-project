# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks the filters of the origin of the nodes name (``origin_risk_ids``; WF-RIS-0060, #1761).

``listNodes`` and ``compareRevisions`` retain the nodes an occurrence merged, those of a risk given
or of any (``Node.origin_risk_id``); a risk that is not an occurred risk of the project is refused.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import ErrorCode
from waterfall.core.risks.interface import occurred_risk_ids
from waterfall.platform.errors import FieldError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def unknown_risks(
    session: Session, project_id: UUID, asked: tuple[UUID, ...] | None
) -> list[FieldError]:
    """Name each risk of ``origin_risk_ids`` that is not an occurred risk of the project (#1761).

    ``UNKNOWN_RISK`` on the place of the identifier in the list (``/query/origin_risk_ids/<n>``).
    """
    if asked is None:
        return []
    known = occurred_risk_ids(session, project_id, asked)
    return [
        FieldError(f"/query/origin_risk_ids/{place}", ErrorCode.UNKNOWN_RISK)
        for place, each in enumerate(asked)
        if each not in known
    ]
