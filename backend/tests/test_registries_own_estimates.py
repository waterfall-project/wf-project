# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the registries of the own estimates act (EP-30, US-3070/L1).

Details of the realization which reprise no Vérif: the parts of a recomposition and of a pruning run
stage by stage whatever the order of their registration; what is done before a marking, by the
worker's transaction, and before the merge of an amendment, by the worker, sees the revision still
current and stops it, nothing written, when it refuses; the mode of a merge is the amendment's
unless one is asked; the state of an own estimate read from its row.
"""

from contextlib import ExitStack
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from amendments_support import opened_amendment
from merges_support import client, costed_project, merged, merging_worker
from sqlalchemy import select

from waterfall.core.revisions.interface import (
    AMENDMENT_MERGE,
    MERGE_MODES,
    OCCURRENCE_MERGE,
    Abandonment,
    BeforeMarking,
    OwnEstimateComposing,
    OwnEstimatePruning,
    StructureMerging,
    abandonments_of,
    compose_parts,
    load_marking,
    own_estimate_state_of,
    prune_parts,
    record_abandonments,
    register_before_marking,
    register_compose,
    register_prune,
)
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from openapi_core import OpenAPI
    from realm import TestRealm
    from risks_support import Costed
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker


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
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the merges."""
    return merging_worker(database, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


# A frame whose parts read nothing of it: the registries hand it on as it is.
FRAME: Any = object()


def test_the_parts_of_a_recomposition_and_of_a_pruning_run_stage_by_stage() -> None:
    # A part of the end registered before a part of the nodes runs after it, and the parts of a
    # stage in the order of their registration; the pruning gives what its parts abandon, each
    # once, in the order told. Withdrawn, a part runs no more.
    ran: list[str] = []

    def composing(name: str) -> Callable[[OwnEstimateComposing], None]:
        def part(given: OwnEstimateComposing) -> None:
            assert given is FRAME
            ran.append(name)

        return part

    lineage, link = uuid4(), (uuid4(), uuid4())

    def pruning(name: str, *abandoned: Abandonment) -> Callable[[OwnEstimatePruning], None]:
        def part(given: OwnEstimatePruning) -> None:
            ran.append(name)
            given.abandoned.extend(abandoned)

        return part

    frame = OwnEstimatePruning(FRAME, uuid4(), uuid4(), uuid4(), uuid4(), FRAME)
    with ExitStack() as registered:
        registered.callback(register_compose("end", composing("end")))
        registered.callback(register_compose("nodes", composing("tasks")))
        registered.callback(register_compose("nodes", composing("lines")))
        compose_parts(FRAME)
        registered.callback(register_prune("pruned", pruning("deleted")))
        registered.callback(register_prune("kept", pruning("tasks", Abandonment(lineage))))
        registered.callback(
            register_prune("kept", pruning("links", Abandonment(link=link), Abandonment(lineage)))
        )
        found = prune_parts(frame)
    assert ran == ["tasks", "lines", "end", "tasks", "links", "deleted"]
    assert found == (Abandonment(lineage), Abandonment(link=link))
    ran.clear()
    compose_parts(FRAME)
    assert prune_parts(OwnEstimatePruning(FRAME, uuid4(), uuid4(), uuid4(), uuid4(), FRAME)) == ()
    assert ran == []


@pytest.mark.parametrize(
    "named", [{}, {"lineage_id": uuid4(), "link": (uuid4(), uuid4())}], ids=["none", "both"]
)
def test_an_abandonment_names_a_node_or_a_link(named: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="a node or a link"):
        Abandonment(**named)


def test_the_state_of_an_own_estimate_is_read_from_its_row() -> None:
    # Whole and up to date while the main structure bears the counter it retained; pruned when it
    # names a revision; consumed once merged. A structure of another kind has none.
    risk, revision = uuid4(), uuid4()
    row = CostStructure(id=uuid4(), kind="risk", risk_id=risk, main_lock_version=4, is_merged=False)
    found = own_estimate_state_of(row, 4)
    assert (found.whole, found.up_to_date, found.consumed) == (True, True, False)
    row.pruned_revision_id, row.is_merged = revision, True
    found = own_estimate_state_of(row, 5)
    assert (found.pruned, found.pruned_revision_id, found.up_to_date, found.consumed) == (
        True,
        revision,
        False,
        True,
    )
    with pytest.raises(ValueError, match="no own estimate"):
        own_estimate_state_of(CostStructure(id=uuid4(), kind="amendment"), 4)


def test_a_merge_is_the_merge_of_an_amendment_unless_its_mode_says_an_occurrence() -> None:
    merging = StructureMerging(FRAME, uuid4(), uuid4(), uuid4(), uuid4(), FRAME, applying=False)
    assert merging.mode == AMENDMENT_MERGE
    assert MERGE_MODES == (AMENDMENT_MERGE, OCCURRENCE_MERGE) == ("amendment", "occurrence")


def _status(session: Session, revision_id: UUID) -> str | None:
    return session.scalar(select(Revision.status).where(Revision.id == revision_id))


def _told(before: BeforeMarking) -> tuple[UUID, UUID | None, str | None]:
    """Give what a module is told before a marking: the revision, the amendment, its status."""
    return before.revision_id, before.merged, _status(before.session, before.revision_id)


def test_what_is_done_before_a_marking_sees_the_revision_current_and_its_refusal_stops_it(
    project: Costed,
) -> None:
    # The modules registered are told before the marking writes, the revision still current; one
    # that refuses fails the marking, the revision left current. Without it, the marking marks.
    told: list[tuple[UUID, UUID | None, str | None]] = []

    def update(before: BeforeMarking) -> None:
        told.append(_told(before))

    def refuse(_: BeforeMarking) -> None:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": "risk_up_to_date"})

    revision_id, database = project.revision_id, project.stage.database
    with ExitStack() as registered:
        registered.callback(register_before_marking(update))
        withdraw = register_before_marking(refuse)
        registered.callback(withdraw)
        with pytest.raises(ConflictError), database.transaction() as session:
            load_marking(session, revision_id, "v1.0", None, Act(None, utc_now()))
        withdraw()
        with logging_context(correlation_id="marking"), database.transaction() as session:
            assert _status(session, revision_id) == "draft"
            load_marking(session, revision_id, "v1.0", None, Act(None, utc_now()))
    assert told == [(revision_id, None, "draft")] * 2
    with database.transaction() as session:
        assert _status(session, revision_id) == "marked"


def test_what_is_done_before_a_marking_is_done_before_the_merge_of_an_amendment(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # The worker tells the modules registered before the merge writes anything, the revision still
    # current, the amendment named; the merge then marks the revision.
    amendment = UUID(opened_amendment(api, project))
    told: list[tuple[UUID, UUID | None, str | None]] = []

    def update(before: BeforeMarking) -> None:
        told.append(_told(before))

    with ExitStack() as registered:
        registered.callback(register_before_marking(update))
        task = merged(api, project, worker, amendment)
    assert task["status"] == "succeeded", task
    assert told == [(project.revision_id, amendment, "draft")]


def test_the_abandonments_written_are_read_back_nodes_then_links(project: Costed) -> None:
    # What the pruning writes of an own estimate is what the recomposition reads: the nodes, then
    # the links. Written on the main structure here, which names no risk: the table names a
    # structure of its revision alone.
    node, link = uuid4(), (uuid4(), uuid4())
    structure = (project.project_id, project.revision_id, project.structure_id)
    with project.stage.database.transaction() as session:
        record_abandonments(session, structure, (), Act(None, utc_now()))
        record_abandonments(
            session, structure, (Abandonment(link=link), Abandonment(node)), Act(None, utc_now())
        )
        found = abandonments_of(session, project.project_id, project.structure_id)
    assert found == (Abandonment(node), Abandonment(link=link))
