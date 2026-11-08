# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The facets of a node other than the task: what a later module registers for its own kind.

A node is a task here, an estimate line by EP-07, whose facet is a table of its module: EP-07
registers, for its kind, the reading of its facet (``listNodes`` returns it), its copy and its
deletion with the node (a revision opened, a node deleted), and the calendars of the roles of its
lines, which the calendar applicable to a task intersects (``calendar_of``, WF-PLA-0010). The
planning knows no other facet than its own: it asks the hooks of the kind (EP-06, "Les points
d'extension").

Declared by US-1380/L1; filled by US-1380/L2: ``calendar_of`` gives the default calendar to a task
whose facets name no calendar — every task until EP-07 —, the intersection of those they name
otherwise; ``calendars_of`` gives it to the tasks of a structure, the default read once.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.planning.calendars import applicable_of, default_calendar
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.revisions.interface import RevisionCopy


@dataclass(frozen=True, slots=True)
class FacetHooks:
    """What the planning asks of the facet of a kind of node.

    ``read(session, project_id, node_ids)`` gives the facet of each node named, by node;
    ``copy(copy)`` copies the facets of the source into the revision opened, the nodes copied found
    in ``copy.identifiers``; ``delete(session, project_id, node_ids)`` deletes the facets of the
    nodes deleted; ``calendars(session, project_id, task_id)`` gives the calendars of the roles of
    the nodes of the kind under a task.
    """

    read: Callable[[Session, UUID, Collection[UUID]], Mapping[UUID, Any]]
    copy: Callable[[RevisionCopy], None]
    delete: Callable[[Session, UUID, Collection[UUID]], None]
    calendars: Callable[[Session, UUID, UUID], Collection[UUID]]


# The hooks of each kind of node other than the task, in the order of their registration.
_FACETS: Registry[tuple[str, FacetHooks]] = Registry("planning.facets")


def register_facet(kind: str, hooks: FacetHooks) -> Callable[[], None]:
    """Add the hooks of the facet of a kind of node; give their withdrawal; refused if held."""
    if kind in facets():
        msg = f"the facet {kind} is registered already"
        raise ValueError(msg)
    return _FACETS.register((kind, hooks))


def facets() -> Mapping[str, FacetHooks]:
    """Give the hooks of each kind of node registered, by kind."""
    return dict(_FACETS.entries())


def calendar_of(
    session: Session, project_id: UUID, task_id: UUID, *, default: Applicable | None = None
) -> Applicable:
    """Give the calendar applicable to a task (WF-PLA-0010).

    The calendars the facets of the kinds registered name under the task, intersected day by day;
    the default calendar when they name none — read here unless ``default`` gives it.
    """
    named = {
        calendar_id
        for hooks in facets().values()
        for calendar_id in hooks.calendars(session, project_id, task_id)
    }
    return applicable_of(session, named, default or default_calendar(session))


def calendars_of(
    session: Session, project_id: UUID, task_ids: Collection[UUID]
) -> dict[UUID, Applicable]:
    """Give the calendar applicable to each task named, the default calendar read once."""
    default = default_calendar(session)
    return {
        task_id: calendar_of(session, project_id, task_id, default=default) for task_id in task_ids
    }
