# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources and their capacity.

Read, listed, created, changed, deactivated and reactivated (WF-REF-0090, 0100).

Empty until US-0850 fills it, but for the questions the categories of cost ask
(``category_has_roles``, ``roles_of_categories``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RoleOfCategory:
    """A role attached to a category, as a refusal names it: active or not (WF-IHM-0090)."""

    resource_role_id: UUID
    code: str
    label: str


def category_has_roles(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a role of resources is attached to, deactivated or not.

    No role can be attached before US-0850 serves them: none is yet, which it replaces.
    """
    del session, category_ids
    return frozenset()


def roles_of_categories(session: Session, category_ids: Collection[UUID]) -> list[RoleOfCategory]:
    """Give the roles attached to the categories given, deactivated ones too, in the order of code.

    The roles a refusal to change the kind of a nature or of a category names (WF-REF-0030,
    WF-REF-0040). None before US-0850.
    """
    del session, category_ids
    return []
