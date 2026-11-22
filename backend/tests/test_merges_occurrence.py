# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mode « survenance » of the merge, on the differentials of the fabrics (US-3100/L1).

The parts the planning and the estimate give of ``register_merge`` when the merge is the
occurrence of a risk (``OCCURRENCE_MERGE``; EP-30, "La survenance"), asked as the task of the
occurrence will ask them: the report, writing nothing, then the application in the same frame,
as ``merge_applying`` does. A task the own estimate abandons is kept and completed whatever its
state; the completed tasks the merge reopens are named; a line designated receives its current
figures alone, a line added a budgeted amount of nought and the trace of the risk; nothing is
marked nor designated. The same differential merged as an amendment keeps its rule.

The task of the occurrence, its withdrawal of the provision and its report through the service
are US-3100/L2's: these tests cite the story, whose criteria they do not close.
"""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from merges_support import client, costed_project, project_of, revision_of
from nodes_support import set_progress
from own_estimates_support import ADDED, MODIFIED, risk_differential
from planning_support import insert_task
from risks_support import MAKING, STUDY, material_line
from sqlalchemy import select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import (
    AMENDMENT_MERGE,
    OCCURRENCE_MERGE,
    MergePart,
    StructureMerging,
    merge_parts,
)
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Generator

    from openapi_core import OpenAPI
    from own_estimates_support import RiskDifferential
    from realm import TestRealm
    from risks_support import Costed
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.revisions.interface import MergeMode
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

pytestmark = pytest.mark.story("US-3100")

DAY = date(2026, 3, 2)
# A task of the main structure without a line, declared before the risk, which its own estimate
# copies; and the task the own estimate adds under it, with its line.
CONTROL = "Contrôle"
SURVEY = ("Sondage", Decimal("50.00"))
# The label of the lines the fabrics write around the service — the provision line among them —,
# that of the line of the task abandoned, and a rank above any at the first level.
PROVISION_LABEL = "Ligne"
ABANDONED_LINE = "Fabrication"
PARKED = 1000


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


@contextmanager
def framed(
    risk: RiskDifferential, mode: MergeMode = OCCURRENCE_MERGE
) -> Generator[StructureMerging]:
    """Give the frame of the merge of the own estimate of a risk, in its transaction."""
    project = risk.project
    with project.stage.database.transaction() as session:
        yield StructureMerging(
            session,
            project.project_id,
            project.revision_id,
            project.structure_id,
            risk.structure_id,
            Act(None, utc_now()),
            applying=False,
            mode=mode,
        )


def reported(risk: RiskDifferential, mode: MergeMode = OCCURRENCE_MERGE) -> MergePart:
    """Give the report of the merge of the own estimate of a risk, which writes nothing."""
    with framed(risk, mode) as merging:
        return merge_parts(merging)


def applied(risk: RiskDifferential) -> tuple[MergePart, date]:
    """Apply the occurrence as its task will: the report, then the application in its frame.

    Give what the application found, and the day it completed its tasks on.
    """
    with framed(risk) as merging:
        assert merge_parts(merging).refusals == ()
        found = merge_parts(replace(merging, applying=True))
        return found, current_day(merging.act.at)


def main_counter(project: Costed) -> int:
    """Read the counter of the main structure of the current revision."""
    with project.stage.database.transaction() as session:
        counter = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == project.structure_id)
        )
    assert counter is not None
    return counter


def changes(found: MergePart) -> list[tuple[str, str, str, list[str]]]:
    """Give the differences of a merge, each by its change, its target, its label, its fields."""
    return [
        (
            str(each["change"]),
            str(each["target"]),
            str(each["label"]),
            [str(name) for name in cast("list[object]", each["fields"])],
        )
        for each in found.differences
    ]


def lineage(session: Session, node_id: UUID) -> UUID:
    """Read the lineage of a node."""
    found = session.scalar(select(Node.lineage_id).where(Node.id == node_id))
    assert found is not None
    return found


def task(project: Costed, label: str) -> Task:
    """Read a task of the main structure by its label, detached."""
    with project.stage.database.transaction() as session:
        row = session.scalars(
            select(Task).where(Task.structure_id == project.structure_id, Task.label == label)
        ).one()
        session.expunge(row)
        return row


def line(project: Costed, named: str | UUID) -> tuple[EstimateLine, UUID | None]:
    """Read a line of the main structure by its label or its node, detached, with its trace."""
    which = (
        EstimateLine.node_id == named if isinstance(named, UUID) else EstimateLine.label == named
    )
    with project.stage.database.transaction() as session:
        row, origin = session.execute(
            select(EstimateLine, Node.origin_risk_id)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == project.structure_id, which)
        ).one()
        session.expunge(row)
        return row, origin


def origin_of_task(project: Costed, label: str) -> UUID | None:
    """Read the trace of a task of the main structure by its label."""
    with project.stage.database.transaction() as session:
        return session.scalar(
            select(Node.origin_risk_id)
            .join(Task, Task.node_id == Node.id)
            .where(Node.structure_id == project.structure_id, Task.label == label)
        )


def with_survey(project: Costed) -> RiskDifferential:
    """Declare the risk of the fabric in a project whose main structure also bears ``CONTROL``.

    ``CONTROL``, a task without a line made before the risk, is copied into its own estimate,
    which adds under it ``SURVEY``, a task bearing a line: in the merge, ``CONTROL`` becomes their
    summary.
    """
    project.tree.made(CONTROL)
    risk = risk_differential(project)
    with project.stage.owner.begin() as connection:
        # Parked at the first level, then put under ``CONTROL``, which bears no other task.
        survey = insert_task(
            connection,
            project.project_id,
            project.revision_id,
            risk.structure_id,
            rank=PARKED,
            label=SURVEY[0],
        )
        connection.execute(
            update(Node).where(Node.id == survey).values(parent_id=risk.nodes[CONTROL], rank=1)
        )
        material_line(
            connection,
            (project.project_id, project.revision_id, risk.structure_id, survey),
            project.costs.material,
            SURVEY[1],
        )
    return risk


# --- The report -----------------------------------------------------------------------------------


def test_an_occurrence_keeps_the_task_it_abandons_not_started_where_an_amendment_removes_it(
    project: Costed,
) -> None:
    # The own estimate adds « Renfort », brings « Plans » from 600 to 700 and abandons
    # « Réalisation », not started. Merged as an occurrence, « Réalisation » is kept, its line and
    # the provision under it with it, and named among the tasks it completes, on no day yet;
    # merged as an amendment, the same differential removes it, its line removed and the provision
    # moved, and completes nothing. Neither reopens a task, and the report writes nothing.
    risk = risk_differential(project)
    counter = main_counter(project)
    occurrence = reported(risk)
    assert changes(occurrence) == [
        ("added", "estimate_line", ADDED[0], []),
        ("updated", "estimate_line", MODIFIED[0], ["unit_disbursement"]),
        ("kept", "task", MAKING, []),
    ]
    with project.stage.database.transaction() as session:
        making = str(lineage(session, project.tasks[MAKING]))
    assert occurrence.completed_tasks == (
        {"lineage_id": making, "label": MAKING, "completed_on": None},
    )
    assert (occurrence.refusals, occurrence.reopened_tasks) == ((), ())
    amendment = reported(risk, AMENDMENT_MERGE)
    assert changes(amendment) == [
        ("added", "estimate_line", ADDED[0], []),
        ("updated", "estimate_line", MODIFIED[0], ["unit_disbursement"]),
        ("updated", "estimate_line", PROVISION_LABEL, ["parent"]),
        ("removed", "task", MAKING, []),
        ("removed", "estimate_line", ABANDONED_LINE, []),
    ]
    assert (amendment.completed_tasks, amendment.reopened_tasks) == ((), ())
    assert main_counter(project) == counter


def test_an_occurrence_names_a_completed_task_whose_line_it_designates_reopened(
    project: Costed,
) -> None:
    # « Étude » completed in the main structure: the own estimate modifies its line « Plans » and
    # adds « Renfort » under it. The occurrence names it reopened, by its node and its label,
    # without refusing; the amendment, whose rule is unchanged, names none.
    risk = risk_differential(project)
    set_progress(project.stage, str(project.tasks[STUDY]), "completed", DAY)
    found = reported(risk)
    assert found.refusals == ()
    assert found.reopened_tasks == ({"node_id": str(project.tasks[STUDY]), "label": STUDY},)
    assert reported(risk, AMENDMENT_MERGE).reopened_tasks == ()


def test_an_occurrence_names_a_completed_task_it_adds_a_subtask_under_reopened(
    project: Costed,
) -> None:
    # « Contrôle », completed and bearing no line, receives « Sondage », which the own estimate
    # adds under it: the occurrence names it reopened; « Étude », not completed, is not named.
    risk = with_survey(project)
    control = task(project, CONTROL)
    set_progress(project.stage, str(control.node_id), "completed", DAY)
    found = reported(risk)
    assert ("added", "task", SURVEY[0], []) in changes(found)
    assert found.reopened_tasks == ({"node_id": str(control.node_id), "label": CONTROL},)


# --- The application ------------------------------------------------------------------------------


def test_an_occurrence_writes_the_current_figures_alone_and_completes_the_task_it_abandons(
    api: ContractClient, project: Costed
) -> None:
    # « Renfort » is created at a budgeted amount of nought, re-estimated at 500, without figures
    # of reference, marked of the risk; « Plans » keeps its budget of 600 and is re-estimated at
    # 700, unmarked; « Réalisation », not started, is completed on the day of the occurrence, its
    # start that day, its line « Fabrication » brought to nought, its budget of 400 kept; the
    # provision line stays as it was, the risk's to withdraw. No revision is marked and no
    # reference designated.
    risk = risk_differential(project)
    provision, _ = line(project, risk.provision_node_id)
    found, day = applied(risk)
    assert found.reopened_tasks == ()
    added, origin = line(project, ADDED[0])
    assert (added.budgeted_amount, added.reestimated_amount, origin) == (
        Decimal("0.00"),
        ADDED[1],
        risk.risk_id,
    )
    assert (
        added.reference_quantity,
        added.reference_hours,
        added.reference_unit_disbursement,
    ) == (None, None, None)
    modified, origin = line(project, MODIFIED[0])
    assert (modified.budgeted_amount, modified.reestimated_amount, origin) == (
        MODIFIED[1],
        MODIFIED[2],
        None,
    )
    making = task(project, MAKING)
    assert (making.progress, making.started_on, making.completed_on) == ("completed", day, day)
    abandoned, origin = line(project, ABANDONED_LINE)
    assert (abandoned.budgeted_amount, abandoned.reestimated_amount, origin) == (
        Decimal("400.00"),
        Decimal("0.00"),
        None,
    )
    assert origin_of_task(project, MAKING) is None
    kept, _ = line(project, risk.provision_node_id)
    assert (kept.budgeted_amount, kept.reestimated_amount, kept.lock_version) == (
        provision.budgeted_amount,
        provision.reestimated_amount,
        provision.lock_version,
    )
    revision = revision_of(api, project, project.revision_id)
    assert revision["status"] == "draft"
    assert project_of(api, project)["reference_revision_id"] is None


def test_an_occurrence_completes_a_started_task_it_abandons_its_start_kept(
    project: Costed,
) -> None:
    # « Réalisation », started, is completed as an amendment completes a started task it removes:
    # on the day of the occurrence, its start kept, and named so.
    risk = risk_differential(project)
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    found, day = applied(risk)
    assert [each["label"] for each in found.completed_tasks] == [MAKING]
    assert found.completed_tasks[0]["completed_on"] == day.isoformat()
    making = task(project, MAKING)
    assert (making.progress, making.started_on, making.completed_on) == ("completed", DAY, day)


def test_an_occurrence_reopens_the_completed_task_whose_line_it_designates(
    project: Costed,
) -> None:
    # « Étude », completed, receives the current figures of « Plans » and the line « Renfort »:
    # it is started again, its start kept, its completion cleared, and named so.
    risk = risk_differential(project)
    set_progress(project.stage, str(project.tasks[STUDY]), "completed", DAY)
    found, _ = applied(risk)
    assert found.reopened_tasks == ({"node_id": str(project.tasks[STUDY]), "label": STUDY},)
    study = task(project, STUDY)
    assert (study.progress, study.started_on, study.completed_on) == ("started", DAY, None)
    assert line(project, MODIFIED[0])[0].reestimated_amount == MODIFIED[2]


def test_an_occurrence_marks_the_tasks_and_lines_it_adds_and_reopens_their_completed_parent(
    project: Costed,
) -> None:
    # « Sondage » and its line, added under « Contrôle », completed, bear the trace of the risk,
    # the line at a budgeted amount of nought; « Contrôle », become their summary, is reopened.
    # What existed before keeps no trace.
    risk = with_survey(project)
    control = task(project, CONTROL)
    set_progress(project.stage, str(control.node_id), "completed", DAY)
    found, _ = applied(risk)
    assert found.reopened_tasks == ({"node_id": str(control.node_id), "label": CONTROL},)
    assert origin_of_task(project, SURVEY[0]) == risk.risk_id
    assert origin_of_task(project, CONTROL) is None
    with project.stage.database.transaction() as session:
        survey = session.execute(
            select(EstimateLine.budgeted_amount, Node.origin_risk_id)
            .join(Node, Node.id == EstimateLine.node_id)
            .join(Task, Task.node_id == Node.parent_id)
            .where(Node.structure_id == project.structure_id, Task.label == SURVEY[0])
        ).one()
    assert tuple(survey) == (Decimal("0.00"), risk.risk_id)
    assert task(project, CONTROL).progress == "started"


def test_the_merge_of_an_amendment_ignores_what_the_estimate_tells_of_the_lines_it_writes(
    project: Costed,
) -> None:
    # The estimate tells the planning the tasks whose lines a merge writes in both modes: an
    # amendment, whose rule keeps a completed task completed, reads nothing of it.
    risk = risk_differential(project)
    set_progress(project.stage, str(project.tasks[STUDY]), "completed", DAY)
    with framed(risk, AMENDMENT_MERGE) as merging:
        found = merge_parts(merging)
        assert merge_parts(merging).reopened_tasks == found.reopened_tasks == ()
