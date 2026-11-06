# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The questions of the minimal reference this module answers.

Whether an active category of labour exists, and an active category of the kind provision
for risks (WF-CYC-0120): a category active under an active nature of that kind. The route of the
minimal reference composes them with those of the resource settings.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.cost_settings.tables import CostCategory, CostType

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

LABOUR = "labor"
PROVISION = "provision"


def _active_category_of_kind(session: Session, kind: str) -> bool:
    """Tell whether a category is active under an active nature of ``kind``."""
    held = select(
        exists().where(
            CostCategory.cost_type_id == CostType.id,
            CostCategory.is_active,
            CostType.is_active,
            CostType.kind == kind,
        )
    )
    return bool(session.scalar(held))


def labour_categories_exist(session: Session) -> bool:
    """Tell whether an active category of labour exists (``active_cost_category``)."""
    return _active_category_of_kind(session, LABOUR)


def provision_category_active(session: Session) -> bool:
    """Tell whether an active category of provision exists (``active_provision_category``)."""
    return _active_category_of_kind(session, PROVISION)
