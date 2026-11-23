# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of a structure grafted under a task of another, or after a milestone (``graft``).

What the occurrence of a risk asks of the planning (WF-RIS-0060; EP-08, "Modules"): the tasks of
its own estimate, with the nodes they bear and their links, copied under the task of the main
structure that bears its provision line — after it when it is a milestone —, the provision line
removed with them, and what that does to the main structure, as its report says it. One function
computes the report and the application (``graft``): without an act, it reads and writes nothing;
with one, it computes the very same graft under the lock of the two structures and writes it, so
that what the report presented is what is written (``grafting``). The judgement of the state of
the project, of the revision and of the risk is the caller's, which holds their locks first.

Filled by US-2620/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import update

from waterfall.core.planning.grafting import GraftAsked, plan_graft, write_graft
from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Graft:
    """A graft asked: the structure grafted, the one grafted into, and the task they go under.

    ``bearer_id`` the task of the structure grafted into: its tasks go last under it, or right after
    it when it is a milestone (WF-RIS-0060); ``removed`` the lines of that structure the graft
    removes, which move no date — the provision line of a risk —; ``origin_risk_id`` the risk each
    node grafted comes from (``Node.origin_risk_id``), none for a graft that comes from none;
    ``imposed`` the identifier and the lineage of the copy of a node the witness imposes, by the
    lineage of the node grafted (US-2650/L1), none for the service.
    """

    project_id: UUID
    source_id: UUID
    target_id: UUID
    bearer_id: UUID
    removed: tuple[UUID, ...] = ()
    origin_risk_id: UUID | None = None
    imposed: Mapping[UUID, tuple[UUID, UUID]] | None = None


@dataclass(frozen=True, slots=True)
class Grafted:
    """What a graft does to the structure grafted into, as its report says it, and its copies.

    ``differences`` as ``ImportDifference``, in the order of the report — the nodes grafted, added,
    in the order of the plan of the structure grafted; the task they go under, updated, unless a
    milestone; the lines removed —; ``refusals`` as ``ReportRefusal``, empty when the graft
    applies; ``copies`` the node each node of the structure grafted is copied under; ``reopened``
    the task they go under, by its node and its label (``ProvisionTask``), when it is completed: a
    warning, not a refusal — become their summary, it is not started again (#4240) —, none else.
    """

    differences: tuple[Mapping[str, object], ...]
    refusals: tuple[Mapping[str, object], ...]
    copies: Mapping[UUID, UUID]
    reopened: Mapping[str, object] | None = None


def graft(session: Session, asked: Graft, act: Act | None = None) -> Grafted:
    """Compute a graft and what it does; and write it, under the locks, when an act is given.

    Without ``act``, nothing is written nor locked: the report. With it, the structure grafted into
    then the structure grafted are locked and read under their lock, the graft refused by the first
    of its reasons (422), else written and the structure redated (``write_graft``).
    """
    plan = plan_graft(
        session,
        GraftAsked(
            asked.project_id,
            asked.source_id,
            asked.target_id,
            asked.bearer_id,
            asked.removed,
            asked.origin_risk_id,
            {} if asked.imposed is None else asked.imposed,
        ),
        lock=act is not None,
    )
    if act is not None:
        write_graft(session, plan, act)
    return Grafted(tuple(plan.differences), tuple(plan.refusals), dict(plan.copies), plan.reopened)


def release_origin(session: Session, project_id: UUID, revision_id: UUID, risk_id: UUID) -> None:
    """Make the nodes of a revision that come from a risk come from none, nothing else touched.

    For the abandonment of a revision that declared a risk and saw it occur: the risk is deleted
    with it, which the nodes it merged name by their key (``Node.origin_risk_id``); they are
    deleted with the revision, after the risk (``register_closing``).
    """
    session.execute(
        update(Node)
        .where(
            Node.project_id == project_id,
            Node.revision_id == revision_id,
            Node.origin_risk_id == risk_id,
        )
        .values(origin_risk_id=None)
        .execution_options(synchronize_session=False)
    )
