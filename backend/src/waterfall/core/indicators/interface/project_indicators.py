# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The earned value indicators of a project, on a scope (``getProjectIndicators``; US-1660).

The reference budget, the planned value, the earned value, the actual cost and the remaining to
commit at the date of the computation, the progresses and the consumption, the two indices and
their variances, the three projections (WF-IND-0010 to WF-IND-0080): computed on the current day
(US-1660/L3), or read as a marking kept them, for a marked revision named or at a date
(US-1670/L2). The zones are classified at the reading, on the thresholds of the day; a project
before In progress is refused (409).

The refusals come in the order of the contract: the project unknown (404), then a project that
never was In progress (409, its state named); then the parameters (422) — a scope that is not a
subproject of the project, ``revision_id`` and ``as_of`` together —, each named at once; then a
``revision_id`` that is not a revision of the project (404, as any object the project does not
have).

On the current day — no revision named, or the current one —, the indicators are computed on the
current revision, or, without one, on the last marked revision with the actual cost of the day
(WF-IND-0010), ``is_stored`` false; the day is that of the time zone of the installation
(``current_day``, US-2200), the instant of the reading its ``computed_at``. The reference is the
project's, read now. One pass reads what every scope needs (``day_documents``).

Declared by US-1660/L1, the socle of EP-10; filled by US-1660/L3 for the current day, by US-1670/L2
for a marking kept.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.computing import Basis, day_documents
from waterfall.core.indicators.interface.stored_documents import stored_document
from waterfall.core.indicators.shaping import Context, classified
from waterfall.core.projects.interface import (
    current_day,
    list_state_transitions,
    project_facts,
    subproject_labels,
)
from waterfall.core.revisions.interface import marked_revisions_at, read_revision_for
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.interface.reading import IndicatorsReading
    from waterfall.core.projects.interface import ProjectFacts
    from waterfall.core.revisions.interface import RevisionRead

IN_PROGRESS = "in_progress"
# The states a project reaches only through In progress; ``abandoned`` may come before or after it.
ONWARD = frozenset({IN_PROGRESS, "completed"})
PROJECT_STATE = "ProjectState"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
SCOPE_POINTER = "/query/scope"
REVISION_POINTER = "/query/revision_id"
DRAFT, MARKED = "draft", "marked"


def _refuse_before_in_progress(session: Session, project_id: UUID, state: str) -> None:
    """Refuse a project that never was In progress: only its estimate has indicators (409)."""
    if state in ONWARD:
        return
    passages = list_state_transitions(session, project_id)
    if not any(each.to_state == IN_PROGRESS for each in passages):
        raise ConflictError(STATE_FORBIDS_OPERATION, {"state": state, "state_enum": PROJECT_STATE})


def _refuse_parameters(session: Session, project_id: UUID, asked: IndicatorsReading) -> None:
    """Refuse an unknown scope and a revision chosen twice, both at once (422)."""
    faults: list[FieldError] = []
    scope = asked.scope
    if isinstance(scope, UUID) and not subproject_labels(session, project_id, [scope]):
        faults.append(FieldError(SCOPE_POINTER, UNKNOWN_SUBPROJECT))
    if asked.revision_id is not None and asked.as_of is not None:
        faults.append(FieldError(REVISION_POINTER, VALIDATION_FAILED))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def _is_of_the_day(facts: ProjectFacts, asked: IndicatorsReading) -> bool:
    """Tell whether the reading asks the current day: no revision named, or the current one."""
    if asked.as_of is not None:
        return False
    return asked.revision_id is None or asked.revision_id == facts.current_revision_id


def _offer_refusal() -> ConflictError:
    """Give the refusal of a revision that kept no indicators of the project: no ``params.state``.

    The project may be In progress now: only the revision was marked before (#1779, G-02).
    """
    return ConflictError(STATE_FORBIDS_OPERATION)


def _last_kept_before(session: Session, project_id: UUID, day: date) -> UUID | None:
    """Give the last revision marked on or before a day that kept the indicators of the project.

    The day is that of the time zone of the installation, as the day of a marking is; the latest
    ``marked_at`` wins, the greatest identifier on a tie, as everywhere the last marked is read.
    """
    marked = marked_revisions_at(session, project_id)
    candidates = [(at, each) for each, at in marked.items() if current_day(at) <= day]
    for _, each in sorted(candidates, reverse=True):
        if stored_document(session, each, "project", PROJECT) is not None:
            return each
    return None


def _kept_indicators(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the indicators a marking kept, of the marked revision named or of the date asked.

    The zones are not classified here: a document keeps the value of each index, never its zone.
    Refused (409, no ``params``) when no document of the project was kept for the revision, the
    scope or the date asked.
    """
    revision_id = asked.revision_id
    if revision_id is None and asked.as_of is not None:
        revision_id = _last_kept_before(session, project_id, asked.as_of)
    if revision_id is None:
        raise _offer_refusal()
    kept = stored_document(session, revision_id, "project", asked.scope)
    if kept is None:
        raise _offer_refusal()
    return kept


@dataclass(frozen=True, slots=True)
class DayReading:
    """What a reading of the current day computes on: the revisions it reads, and its context."""

    basis: Basis
    context: Context


def day_reading(session: Session, project_id: UUID, asked: IndicatorsReading) -> DayReading | None:
    """Refuse what the contract refuses, then say what the current day is computed on.

    The refusals come in the order of the contract (the module's docstring); none when the reading
    asks a marked revision or a date, which a marking kept (``None``). A reading of the day is on
    the current revision, or, without one, the last marked revision; the curves read it as the
    indicators do (US-1690/L2).
    """
    facts = project_facts(session, project_id)
    _refuse_before_in_progress(session, project_id, facts.state)
    _refuse_parameters(session, project_id, asked)
    named: RevisionRead | None = None
    if asked.revision_id is not None:
        named = read_revision_for(session, project_id, asked.revision_id)
    if not _is_of_the_day(facts, asked):
        return None
    read = named if named is not None else read_revision_for(session, project_id, None)
    status = MARKED if read.marked else DRAFT
    context = Context(read.revision_id, status, asked.at, asked.scope, is_stored=False)
    return DayReading(Basis(project_id, read.revision_id, facts.reference_revision_id), context)


def project_indicators(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the indicators of a project on the scope and for the revision a reading asks."""
    reading = day_reading(session, project_id, asked)
    if reading is None:
        document = _kept_indicators(session, project_id, asked)
    else:
        scope = asked.scope
        document = day_documents(session, reading.basis, reading.context, (scope,))[scope]
    return classified(document, read_reference_settings(session).index_thresholds)
