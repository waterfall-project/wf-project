# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks attached to the work breakdown: what the planning tells the work breakdown of them.

A registry of this module (EP-06, "Les points d'extension"), filled by the planning at the import of
its interface: whether a task of a marked revision bears a work package or an order item
(``work_breakdown_item_cited``), the lock of the rows that bear the elements removed, taken before
the elements are (``hold_work_breakdown_items``, US-2250/L3), and the withdrawal of its attachment
from the tasks of the current revision (``detach_work_breakdown_item``). ``set_work_breakdown`` asks
the three of the elements it removes (US-1380/L3): it marks deleted an element a marked revision
cites, deletes it otherwise, and detaches the tasks of the current revision from it (WF-PLA-0170).

Declared by US-1380/L1, which registers nothing; US-1380/L3 fills it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class Attachments:
    """What a module tells of its rows attached to an element of the work breakdown.

    ``cited(session, item_id)`` says whether a row of a marked revision bears the element;
    ``detach(session, project_id, item_id)`` withdraws it from the rows of the current revision;
    ``hold(session, project_id, item_ids)`` locks what those rows are written under, before the
    elements are locked.
    """

    cited: Callable[[Session, UUID], bool]
    detach: Callable[[Session, UUID, UUID], None]
    hold: Callable[[Session, UUID, Collection[UUID]], None]


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


def hold_items(session: Session, project_id: UUID, item_ids: Collection[UUID]) -> None:
    """Lock what the rows that bear elements of the work breakdown are written under, by each.

    Asked before the elements are written or locked: a module writes its rows under its own locks,
    which a write of its own takes before it shares the element it attaches a row to.
    """
    for attachments in _ATTACHMENTS.entries():
        attachments.hold(session, project_id, item_ids)
