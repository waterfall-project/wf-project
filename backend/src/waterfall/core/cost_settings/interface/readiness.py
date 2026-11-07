# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The questions of the minimal reference this module answers.

Whether an active category of labour exists, and an active category of the kind provision
for risks (WF-CYC-0120): a category active under an active nature of that kind.

This module also composes the four questions of the minimal reference, its own and those of the
resource settings, which it may import: ``missing_prerequisites`` names those that miss, in the
order of ``ReferenceReadiness.missing``, for the route of the minimal reference and for the
creation of a project alike (#2154).
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import (
    active_role_exists,
    default_calendar_has_hours,
)

if TYPE_CHECKING:
    from collections.abc import Callable

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


# The questions of the minimal reference, in the order of the enumeration of the contract
# (``MissingEnum``): the name of each prerequisite, and the question that tells whether it is held.
PREREQUISITES: tuple[tuple[str, Callable[[Session], bool]], ...] = (
    ("default_calendar_with_hours", default_calendar_has_hours),
    ("active_cost_category", labour_categories_exist),
    ("active_provision_category", provision_category_active),
    ("active_resource_role", active_role_exists),
)


def missing_prerequisites(session: Session) -> tuple[str, ...]:
    """Name the prerequisites of the minimal reference that miss, in the order of the contract."""
    return tuple(name for name, held in PREREQUISITES if not held(session))
