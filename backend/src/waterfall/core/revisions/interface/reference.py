# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference revision of a project: its designation, and what it asks of the revision.

A marked revision is designated reference while the project has neither an actual cost nor a
revision marked since the last designation (WF-REV-0040); it must bear tasks and lines
(``revision_has_tasks_and_lines``, WF-CYC-0030), a question this module asks of those of the
planning and of the estimate, which EP-06 and EP-07 fill: always false until then.

Declared by US-0910/L1, without effect: US-0980/L2 fills the designation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def designate_reference(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Designate a marked revision reference of its project (``designateReferenceRevision``)."""
    msg = "designate_reference is filled by US-0980/L2"
    raise NotImplementedError(msg)


def revision_has_tasks_and_lines(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears tasks and lines of estimate: never, until EP-06 and EP-07."""
    del session, revision_id
    return False
