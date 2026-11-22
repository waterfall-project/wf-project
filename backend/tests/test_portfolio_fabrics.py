# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fabrics every lot of the back of EP-11 starts from (``portfolio_support``, US-2670/L1).

Tests of the tools of the tests, which cover no requirement: the four projects, each in its state
by the transitions of the chronology, at its instants; each marked, without a current revision, its
probability kept by the marking of an offer; the indicators of the project kept by a marking In
progress alone, and the estimate of each priced by its two lines.
"""

from typing import TYPE_CHECKING

import pytest
from portfolio_support import (
    COMPLETED_ON,
    DESIGNATED,
    LOST_ON,
    LOST_PROBABILITY,
    LOST_REASON,
    OFFER,
    OFFER_MARKED,
    OFFER_PROBABILITY,
    OFFERS_MARKED,
    OFFERS_OPENED,
    OPENED,
    REVIEW,
    REVIEW_MARKED,
    Portfolio,
    portfolio,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select

from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import list_state_transitions
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import Revision

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The estimate of each project: eight hours at 65.00, and a unit of material at 1 000.00.
ESTIMATE = "1520.00"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def test_each_project_reached_its_state_by_the_transitions_of_the_chronology(
    fabrics: Portfolio,
) -> None:
    # The state of a project at a date is that of its last transition dated that day or before
    # (WF-CYC-0130): each is written at the instant of its fact, the reason of the loss kept.
    priced = [(None, "created", None), ("created", "pricing", None)]
    expected = {
        fabrics.in_progress.project_id: [
            *[(*each[:2], OPENED, None) for each in priced],
            ("pricing", "in_progress", DESIGNATED, None),
        ],
        fabrics.offer.project_id: [(*each[:2], OFFERS_OPENED, None) for each in priced],
        fabrics.completed.project_id: [
            *[(*each[:2], OPENED, None) for each in priced],
            ("pricing", "in_progress", DESIGNATED, None),
            ("in_progress", "completed", COMPLETED_ON, None),
        ],
        fabrics.lost.project_id: [
            *[(*each[:2], OFFERS_OPENED, None) for each in priced],
            ("pricing", "lost", LOST_ON, LOST_REASON),
        ],
    }
    with fabrics.stage.database.transaction() as session:
        found = {
            project_id: [
                (each.from_state, each.to_state, each.occurred_at, each.reason)
                for each in list_state_transitions(session, project_id)
            ]
            for project_id in expected
        }
        states = {
            row.id: row.state
            for row in session.execute(
                select(Project.id, Project.state).where(Project.id.in_(list(expected)))
            )
        }
    assert found == expected
    assert states == {each.project_id: each.state for each in fabrics.projects}


def test_each_project_is_marked_its_probability_and_its_indicators_kept(fabrics: Portfolio) -> None:
    # Each revision marked at its instant, none current; an offer keeps its probability at its
    # marking (EP-07), and only a marking In progress keeps the indicators of the project (EP-10).
    assert {name: at for name, (_, at) in fabrics.in_progress.marked.items()} == {
        OFFER: OFFER_MARKED,
        REVIEW: REVIEW_MARKED,
    }
    assert fabrics.completed.marked.keys() == {OFFER, REVIEW}
    assert [at for _, at in fabrics.offer.marked.values()] == [OFFERS_MARKED]
    assert [at for _, at in fabrics.lost.marked.values()] == [OFFERS_MARKED]
    probabilities = {
        fabrics.offer.marked[OFFER][0]: OFFER_PROBABILITY,
        fabrics.lost.marked[OFFER][0]: LOST_PROBABILITY,
    }
    revisions = [revision for each in fabrics.projects for revision, _ in each.marked.values()]
    with fabrics.stage.database.transaction() as session:
        rows = session.execute(
            select(
                Revision.id, Revision.status, Revision.marked_at, Revision.win_probability
            ).where(Revision.project_id.in_([each.project_id for each in fabrics.projects]))
        ).all()
        kept = session.execute(
            select(
                RevisionIndicator.revision_id, RevisionIndicator.kind, RevisionIndicator.document
            ).where(RevisionIndicator.scope == "project")
        ).all()
    marked = {revision: at for each in fabrics.projects for revision, at in each.marked.values()}
    assert {row.id: (row.status, row.marked_at) for row in rows} == {
        revision: ("marked", at) for revision, at in marked.items()
    }
    assert {row.id: row.win_probability for row in rows if row.id in probabilities} == probabilities
    with_project = {revision for revision, kind, _ in kept if kind == "project"}
    reviews = {fabrics.in_progress.marked[REVIEW][0], fabrics.completed.marked[REVIEW][0]}
    assert with_project == reviews
    estimates = {
        revision: document["total"]["value"]
        for revision, kind, document in kept
        if kind == "estimate"
    }
    assert estimates == dict.fromkeys(revisions, ESTIMATE)
