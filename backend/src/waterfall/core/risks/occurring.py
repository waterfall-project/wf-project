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

Filled by US-2620/L1; the application, under the locks, is US-2620/L2's.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import round_to_cent, structure_amounts
from waterfall.core.planning.interface import Graft, bearing_of, graft
from waterfall.core.projects.interface import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    no_background_task_running,
    project_facts,
)
from waterfall.core.revisions.interface import aimed_structure, structure_facts
from waterfall.core.risks.commands import (
    IDENTIFIED,
    OCCURRED,
    RiskStanding,
    is_terminal,
    risk_conditions,
)
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.reading import read_found

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskState

REFERENCE_DESIGNATED = "reference_revision_designated"
DECLARE_OCCURRENCE = "declare_occurrence"


@dataclass(frozen=True, slots=True)
class OccurrenceReport:
    """What the occurrence of a risk would do (``RiskOccurrenceReport``), and the counters read.

    ``differences`` as ``ImportDifference``, ``refusals`` as ``ReportRefusal``; the provision line
    the occurrence removes, by its amount.
    """

    main_structure_lock_version: int
    risk_lock_version: int
    creates_current_revision: bool
    differences: tuple[Mapping[str, object], ...]
    provision_amount: Decimal
    refusals: tuple[Mapping[str, object], ...]


def _state(state: str) -> RiskState:
    """Give the state of an evaluation as the contract names it."""
    return "identified" if state == IDENTIFIED else "occurred" if state == OCCURRED else "dismissed"


def _judge_project(session: Session, project_id: UUID) -> None:
    """Refuse the occurrence by the first condition of the project it lacks (409)."""
    facts = project_facts(session, project_id)
    if is_terminal(facts.state):
        raise refuse(PROJECT_NOT_TERMINAL)
    if facts.reference_revision_id is None:
        raise refuse(REFERENCE_DESIGNATED)
    if not no_background_task_running(session, project_id):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)


def report_occurrence(
    session: Session, project_id: UUID, risk_id: UUID, viewer: Viewer
) -> OccurrenceReport:
    """Tell what the occurrence of an identified risk would do, writing nothing; or refuse."""
    _judge_project(session, project_id)
    found = read_found(session, project_id, risk_id, None)
    risk, evaluation = found.risk, found.evaluation
    current = project_facts(session, project_id).current_revision_id is not None
    standing = RiskStanding(_state(evaluation.state), cited=False, terminal=False, current=current)
    missing = risk_conditions(DECLARE_OCCURRENCE, standing, viewer.permissions)
    if missing:
        raise refuse(missing[0])
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
    severity = structure_amounts(session, project_id, {evaluation.structure_id})[
        evaluation.structure_id
    ]
    return OccurrenceReport(
        main_structure_lock_version=structure_facts(
            session, project_id, main, lock=False
        ).lock_version,
        risk_lock_version=risk.lock_version,
        creates_current_revision=not current,
        differences=grafted.differences,
        provision_amount=round_to_cent(severity * evaluation.probability),
        refusals=grafted.refusals,
    )
