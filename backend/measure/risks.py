# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of a differential and the occurrence of a risk (EP-08, US-2650/L2), rolled back.

``make measure-core`` reads their duration, without an objective (the definition of done of EP-08,
decision of the author of 2026-11-17): the merge of a differential the measure opens itself, one
cell entered in it, merged by the witness loader (``load_merge``) under the version name
``measure``, without a description; the occurrence of an identified risk of the project, its own
estimate merged into the main structure in the mode occurrence (``load_occurrence``; EP-30). Each
is the loader's call, which runs the worker's own merge or occurrence with no report to confirm:
the merge marks the revision and makes it the reference as the worker does, and updates the
differential first if it is out of date. The transaction is rolled back whole: the next measure,
and the other parts, read the witness as it was.
"""

from functools import partial
from time import perf_counter
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from measure.figures import summarise
from measure.report import Measure
from measure.target import MeasureError
from measure.writing import entered_leaf, entry
from waterfall.core.planning.interface import (
    NodeFilters,
    Place,
    Writer,
    list_nodes,
    load_merge,
    open_differential,
    update_task_facet,
)
from waterfall.core.projects.interface import Viewer
from waterfall.core.risks.interface import (
    OccurrenceLoad,
    RiskFilters,
    RiskPage,
    RiskSort,
    list_risks,
    load_occurrence,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from measure.target import Target
    from waterfall.platform.database import Database

_LABEL = "measure"
_VERSION = "measure"
_PAGE = RiskPage(limit=100, offset=0)


def _rolled_back(database: Database, once: Callable[[Session], float]) -> float:
    with Session(database.engine) as session:
        try:
            return once(session)
        finally:
            session.rollback()


def _measured(
    name: str, database: Database, once: Callable[[Session], float], runs: int
) -> Measure:
    """Play the operation once to warm it, not counted, then ``runs`` times, each rolled back."""
    _rolled_back(database, once)
    return Measure(
        name=name, summary=summarise([_rolled_back(database, once) for _ in range(runs)])
    )


def _merged(session: Session, *, target: Target) -> float:
    """Open a differential, enter a duration in it, then time its merge into the current one."""
    place = target.place
    act = Act(target.manager_id, utc_now())
    revision = (place.project_id, place.revision_id)
    opened = open_differential(session, revision, _LABEL, Writer(act, None))
    session.flush()
    amendment = Place(place.project_id, place.revision_id, opened)
    leaf = entered_leaf(list_nodes(session, amendment, NodeFilters(kinds=("task",))).items)
    update_task_facet(session, amendment, leaf.node_id, entry(leaf, "duration"), Writer(act, None))
    session.flush()
    started = perf_counter()
    load_merge(session, amendment, (_VERSION, None), act)
    session.flush()
    return perf_counter() - started


def _identified(session: Session, target: Target) -> UUID:
    viewer = Viewer(target.manager_id, ())
    found = list_risks(
        session,
        target.place.project_id,
        (RiskFilters(states=("identified",)), RiskSort(), _PAGE),
        viewer,
    )
    if not found.risks:
        message = "the project has no identified risk the occurrence can be measured on"
        raise MeasureError(message)
    return found.risks[0].risk_id


def _occurred(session: Session, *, target: Target) -> float:
    """Time the occurrence of an identified risk of the project: its own estimate merged."""
    risk_id = _identified(session, target)
    act = Act(target.manager_id, utc_now())
    started = perf_counter()
    load_occurrence(session, target.place.project_id, OccurrenceLoad(risk_id), act)
    session.flush()
    return perf_counter() - started


def measure_merge(database: Database, target: Target, runs: int) -> Measure:
    """Measure the merge of a differential: opened and written in the transaction, then merged."""
    return _measured("merge a differential", database, partial(_merged, target=target), runs)


def measure_occurrence(database: Database, target: Target, runs: int) -> Measure:
    """Measure the occurrence of an identified risk, its own estimate merged into the main one."""
    return _measured("occur a risk", database, partial(_occurred, target=target), runs)
