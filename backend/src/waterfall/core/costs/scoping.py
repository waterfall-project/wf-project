# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exclusion of a line from the scope tracked, and its reinstatement, private to the module.

An update of the line alone, idempotent and without a counter (WF-CRE-0030): the state aimed at and
the reason are written, the reason none when the line is reinstated; a request that asks the state
the line has, with the reason it has, writes and inscribes nothing. It is decided under the lock of
the project, as the application of an import is, so that an exclusion neither crosses an import nor
another exclusion of the same line. Each change is inscribed in the journal of audit, the line
named by its document and its item; it never enters the history that can be undone (WF-SEC-0030).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.costs.reading import CostLineView, views_of
from waterfall.core.costs.tables import CostLine
from waterfall.core.projects.interface import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    lock_project,
    project_code,
    project_label,
)
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, Inscription, record
from waterfall.platform.errors import ConflictError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
NOT_FOUND = "NOT_FOUND"
PROJECT_IN_PROGRESS = "project_in_progress"
IN_PROGRESS = "in_progress"


@dataclass(frozen=True, slots=True)
class ScopeChange:
    """The state aimed at: tracked or excluded, and the reason of an exclusion (none to give)."""

    is_in_tracked_scope: bool
    reason: str | None = None


def _refused(condition: str) -> ConflictError:
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})


def judge_exclusion(session: Session, project_id: UUID) -> None:
    """Lock a project, then judge the conditions of its command ``exclude_cost_lines`` under it.

    A terminal project first (``project_not_terminal``), then one that is not In progress
    (``project_in_progress``): 409, as the contract lists them, nothing written. The witness, which
    writes at the instant its chronology imposes, does not judge them.
    """
    facts = lock_project(session, project_id)
    if facts.state in TERMINAL:
        raise _refused(PROJECT_NOT_TERMINAL)
    if facts.state != IN_PROGRESS:
        raise _refused(PROJECT_IN_PROGRESS)


def set_scope(
    session: Session, project_id: UUID, cost_line_id: UUID, change: ScopeChange, act: Act
) -> CostLineView:
    """Exclude a line of a project, or reinstate it; give it as it stands.

    Under the lock of the project, taken here if its caller has not taken it. A line the project
    does not have is unknown (404).
    """
    lock_project(session, project_id)
    line = session.scalar(
        select(CostLine).where(CostLine.id == cost_line_id, CostLine.project_id == project_id)
    )
    if line is None:
        raise NotFoundError(NOT_FOUND)
    reason = None if change.is_in_tracked_scope else change.reason
    if line.is_in_tracked_scope != change.is_in_tracked_scope or line.excluded_reason != reason:
        line.is_in_tracked_scope = change.is_in_tracked_scope
        line.excluded_reason = reason
        line.updated_at = act.at
        line.updated_by = act.author
        session.flush()
        _inscribe(session, line, act)
    return views_of(session, project_id, [line])[0]


def _inscribe(session: Session, line: CostLine, act: Act) -> None:
    """Inscribe the exclusion or the reinstatement of a line in the journal of audit."""
    item = "" if line.document_item is None else f" / {line.document_item}"
    audited = AuditObject("cost_line", line.id, f"{line.document_number}{item}")
    project = AuditProject(
        line.project_id,
        project_code(session, line.project_id),
        project_label(session, line.project_id) or "",
    )
    action = "cost_line_reinstate" if line.is_in_tracked_scope else "cost_line_exclude"
    actor = inscribed_actor(session, act.author)
    # The object says the action in full (``AuditParams``): its document and its item, no parameter.
    record(session, Inscription(action, actor, audited, act.at, project))
