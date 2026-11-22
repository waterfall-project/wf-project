# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report of the occurrence of a risk, private to the module (``getRiskOccurrenceReport``).

A read, which writes nothing (WF-RIS-0060; ``docs/api/DECISIONS.md``, "Le compte rendu préalable
de la survenance d'un risque", #1453). It is judged in the order of the 409 of the occurrence
(``declareRiskOccurrence``): the conditions of the project — a terminal project
(``project_not_terminal``), a project without a reference (``reference_revision_designated``), a
background task that writes in it (``no_background_task_running``) —, then, the risk read (404),
those of the risk, as its command ``declare_occurrence`` names them: a risk that is not identified
(``risk_identified``), and, without a current revision, the permission to create it
(``may_create_revision``).

The report is the graft of the planning computed without being written (``graft``): the tasks and
the lines of the own estimate added under the task that bears the provision line — after it, a
milestone —, that task changed, the provision line removed; and the reasons that refuse it. It is
judged in the revision the risk is read in: the current one, or, without one, the last marked one,
which the occurrence would copy first (``creates_current_revision``, #790). The counters read are
those of the main structure of that revision and of the risk, which the confirmation sends back;
the provision removed is the amount of the line, the severity weighted by the probability.

Filled by US-2620/L1; the application, under the locks, is US-2620/L2's (``applying``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.interface import provision_amount
from waterfall.core.planning.interface import Graft, bearing_of, graft
from waterfall.core.projects.interface import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    no_background_task_running,
    project_facts,
)
from waterfall.core.revisions.interface import aimed_structure, structure_facts
from waterfall.core.risks.commands import (
    OCCURRED,
    RiskStanding,
    is_terminal,
    risk_conditions,
    state_named,
)
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.reading import Found, read_found
from waterfall.core.risks.tables import RiskEvaluation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer

REFERENCE_DESIGNATED = "reference_revision_designated"
DECLARE_OCCURRENCE = "declare_occurrence"


@dataclass(frozen=True, slots=True)
class OccurrenceReport:
    """What the occurrence of a risk would do (``RiskOccurrenceReport``), and the counters read.

    ``differences`` as ``ImportDifference``, ``refusals`` as ``ReportRefusal``; the provision line
    the occurrence removes, by its amount; the planning start of the own estimate when it precedes
    the day of the read, which warns and refuses nothing (#4133); the task that bears the
    provision line when it is completed, by its node and its label, which the graft reopens: a
    warning too (#4240).
    """

    main_structure_lock_version: int
    risk_lock_version: int
    creates_current_revision: bool
    differences: tuple[Mapping[str, object], ...]
    provision_amount: Decimal
    refusals: tuple[Mapping[str, object], ...]
    own_estimate_past_planning_start_on: date | None = None
    completed_provision_task: Mapping[str, object] | None = None


def judge_project(session: Session, project_id: UUID, besides: UUID | None = None) -> None:
    """Refuse the occurrence by the first condition of the project it lacks (409).

    ``besides`` is the task of the occurrence itself, which does not count as a task that writes.
    """
    facts = project_facts(session, project_id)
    if is_terminal(facts.state):
        raise refuse(PROJECT_NOT_TERMINAL)
    if facts.reference_revision_id is None:
        raise refuse(REFERENCE_DESIGNATED)
    if not no_background_task_running(session, project_id, besides):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)


def judge_risk(session: Session, project_id: UUID, risk_id: UUID, viewer: Viewer) -> Found:
    """Read the risk (404) and refuse the occurrence by the first condition of the risk it lacks.

    After those of the project: a risk that is not identified (``risk_identified``), and, without a
    current revision, the permission to create it (``may_create_revision``). Give the risk read in
    the revision the occurrence is judged in.
    """
    found = read_found(session, project_id, risk_id, None)
    current = project_facts(session, project_id).current_revision_id is not None
    standing = RiskStanding(
        state_named(found.evaluation.state), cited=False, terminal=False, current=current
    )
    missing = risk_conditions(DECLARE_OCCURRENCE, standing, viewer.permissions)
    if missing:
        raise refuse(missing[0])
    return found


def report_occurrence(
    session: Session, project_id: UUID, risk_id: UUID, viewer: Viewer, today: date
) -> OccurrenceReport:
    """Tell what the occurrence of an identified risk would do, writing nothing; or refuse.

    ``today`` is the day of the read, in the time zone of the installation: an own estimate whose
    planning starts before it is told (#4133).
    """
    judge_project(session, project_id)
    found = judge_risk(session, project_id, risk_id, viewer)
    risk, evaluation = found.risk, found.evaluation
    current = project_facts(session, project_id).current_revision_id is not None
    line = evaluation.provision_node_id
    revision_id = evaluation.revision_id
    main = aimed_structure(session, project_id, revision_id, None)
    if line is None or main is None:
        msg = "an identified risk bears its provision line in the main structure"
        raise ValueError(msg)
    bearer = bearing_of(session, project_id, (line,))[line].node_id
    grafted = graft(
        session,
        Graft(project_id, evaluation.structure_id, main, bearer, (line,), risk_id),
    )
    provision = provision_amount(session, project_id, line)
    start = structure_facts(session, project_id, evaluation.structure_id, lock=False)
    return OccurrenceReport(
        main_structure_lock_version=structure_facts(
            session, project_id, main, lock=False
        ).lock_version,
        risk_lock_version=risk.lock_version,
        creates_current_revision=not current,
        differences=grafted.differences,
        provision_amount=provision,
        refusals=grafted.refusals,
        own_estimate_past_planning_start_on=(
            start.planning_start_on if start.planning_start_on < today else None
        ),
        completed_provision_task=grafted.reopened,
    )


def occurred_among(
    session: Session, project_id: UUID, risk_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give those of the risks named that occurred, in one revision of the project or another.

    The risks the filters of the origin may name (``origin_risk_ids``, WF-RIS-0060): an occurrence
    abandoned with its revision leaves none.
    """
    if not risk_ids:
        return frozenset()
    return frozenset(
        session.scalars(
            select(RiskEvaluation.risk_id)
            .where(
                RiskEvaluation.project_id == project_id,
                RiskEvaluation.risk_id.in_(list(risk_ids)),
                RiskEvaluation.state == OCCURRED,
            )
            .distinct()
        )
    )
