# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks attached to the work breakdown: what the planning tells the work breakdown of them.

A registry of this module (EP-06, "Les points d'extension"), filled by the planning at the import of
its interface: whether a task of a marked revision bears a work package or an order item
(``work_breakdown_item_cited``), and the withdrawal of its attachment from the tasks of the current
revision (``detach_work_breakdown_item``). ``set_work_breakdown`` asks both of an element it
removes (US-1380/L3): it marks deleted an element a marked revision cites, deletes it otherwise,
and detaches the tasks of the current revision from it (WF-PLA-0170).

Declared by US-1380/L1, which registers nothing; US-1380/L3 fills it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class Attachments:
    """What a module tells of its rows attached to an element of the work breakdown.

    ``cited(session, item_id)`` says whether a row of a marked revision bears the element;
    ``detach(session, project_id, item_id)`` withdraws it from the rows of the current revision.
    """

    cited: Callable[[Session, UUID], bool]
    detach: Callable[[Session, UUID, UUID], None]


# What each module tells of its rows attached to the work breakdown, in their order.
_ATTACHMENTS: Registry[Attachments] = Registry("projects.attachments")


def register_attachments(attachments: Attachments) -> Callable[[], None]:
    """Add what a module tells of its rows attached to the work breakdown; give its withdrawal."""
    return _ATTACHMENTS.register(attachments)


def item_cited(session: Session, item_id: UUID) -> bool:
    """Tell whether a row of a marked revision bears an element of the work breakdown, by each."""
    return any(attachments.cited(session, item_id) for attachments in _ATTACHMENTS.entries())


def detach_item(session: Session, project_id: UUID, item_id: UUID) -> None:
    """Withdraw an element of the work breakdown from the rows of the current revision, by each."""
    for attachments in _ATTACHMENTS.entries():
        attachments.detach(session, project_id, item_id)
