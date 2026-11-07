# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference revision of a project: its designation, and what it asks of the revision.

A marked revision is designated reference while the project has neither an actual cost nor a
revision marked since the last designation (WF-REV-0040); it must bear tasks and lines
(``revision_has_tasks_and_lines``, WF-CYC-0030), a question this module asks of those of the
planning and of the estimate, which EP-06 and EP-07 register (``register_tasks_and_lines``):
always false until then.

Declared by US-0910/L1, without effect: US-0980/L2 fills the designation.
"""

from typing import TYPE_CHECKING

from waterfall.core.revisions.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The questions a revision answers to bear tasks and lines: EP-06 its tasks, EP-07 its lines.
_TASKS_AND_LINES: Registry[Callable[[Session, UUID], bool]] = Registry()


def designate_reference(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Designate a marked revision reference of its project (``designateReferenceRevision``)."""
    msg = "designate_reference is filled by US-0980/L2"
    raise NotImplementedError(msg)


def register_tasks_and_lines(question: Callable[[Session, UUID], bool]) -> Callable[[], None]:
    """Add a question a revision must answer yes to bear tasks and lines; give its withdrawal."""
    return _TASKS_AND_LINES.register(question)


def revision_has_tasks_and_lines(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears tasks and lines of estimate: every question registered says so.

    None registered, the revision bears none: false until EP-06 and EP-07 register theirs.
    """
    questions = _TASKS_AND_LINES.entries()
    return bool(questions) and all(question(session, revision_id) for question in questions)
