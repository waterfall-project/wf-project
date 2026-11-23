# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the registries of the revisions act (#2180; EP-06 to EP-08).

Details of the realization which reprise no Vérif: the closing of a revision, what its marking keeps
and what follows the designation of a reference, the categories a line employs, the parts of a
merge and the end of a merge judged once.
"""

from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import give_a_line
from planning_support import give_a_task
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.core.cost_settings.interface import category_is_employed, register_employment
from waterfall.core.history.interface import (
    close_history,
)
from waterfall.core.planning.interface import (
    delete_nodes,
)
from waterfall.core.revisions.interface import (
    MergePart,
    MergePartError,
    ReferenceDesignated,
    RevisionClosing,
    RevisionMarking,
    StructureMerging,
    closers,
    mark_revision,
    merge_parts,
    register_closing,
    register_designation,
    register_indicators,
    register_marking,
    register_merge,
    register_merge_end,
)
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


@dataclass(frozen=True)
class Closed:
    """A closing a module received: the revision, why, and its status then."""

    revision_id: UUID
    kind: str
    status: str


def test_a_closing_registered_runs_before_the_revision_is_marked_or_abandoned(
    api: ContractClient, stage: Scene
) -> None:
    closed: list[Closed] = []

    def close(closing: RevisionClosing) -> None:
        status = closing.session.scalar(
            select(Revision.status).where(Revision.id == closing.revision_id)
        )
        closed.append(Closed(closing.revision_id, closing.kind, str(status)))

    with ExitStack() as registered:
        registered.callback(register_closing("content", close))
        marked = open_revision(api, stage)
        with (
            logging_context(correlation_id="marking"),
            Session(stage.owner) as session,
            session.begin(),
        ):
            mark_revision(session, UUID(marked["revision_id"]), "v1.0", None, Act(None, utc_now()))
        abandoned = open_revision(api, stage)
        path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{abandoned['revision_id']}"
        response = api.delete(
            f"{path}?lock_version={abandoned['lock_version']}", headers=stage.manager.headers
        )
        assert response.status_code == 204, response.text
    assert closed == [
        Closed(UUID(marked["revision_id"]), "marked", "draft"),
        Closed(UUID(abandoned["revision_id"]), "abandoned", "draft"),
    ]


def test_the_closings_run_stage_by_stage_whatever_the_order_of_their_registration() -> None:
    # The history and its plans before the content of the revision (EP-06, "Les points
    # d'extension"): a part of the content registered first still runs after a part of the history
    # registered later, and the planning's nodes after the history's stacks in any process.
    def content(closing: RevisionClosing) -> None:
        del closing

    def history(closing: RevisionClosing) -> None:
        del closing

    with ExitStack() as registered:
        registered.callback(register_closing("content", content))
        registered.callback(register_closing("history", history))
        ordered = closers()
    assert ordered.index(history) < ordered.index(content)
    assert closers().index(close_history) < closers().index(delete_nodes)


def test_a_marking_registered_keeps_its_part_before_the_indicators_of_the_revision(
    api: ContractClient, stage: Scene
) -> None:
    # What EP-07 keeps of a revision being marked — its images, its rates —, in the transaction of
    # the marking, the revision judged and still current, before its indicators are computed.
    ran: list[tuple[str, UUID, str]] = []

    def keep(marking: RevisionMarking) -> None:
        status = marking.session.scalar(
            select(Revision.status).where(Revision.id == marking.revision_id)
        )
        assert (marking.project_id, marking.at) == (UUID(stage.project["project_id"]), at)
        ran.append(("kept", marking.revision_id, str(status)))

    def compute(_session: Session, revision_id: UUID, act: Act) -> None:
        # The act of the marking: its instant, which the indicators are computed at (EP-10).
        assert act.at == at
        ran.append(("computed", revision_id, "draft"))

    at = utc_now()
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    with ExitStack() as registered:
        registered.callback(register_marking(keep))
        registered.callback(register_indicators(compute))
        with (
            logging_context(correlation_id="marking"),
            Session(stage.owner) as session,
            session.begin(),
        ):
            mark_revision(session, revision_id, "v1.0", None, Act(None, at))
    assert ran == [("kept", revision_id, "draft"), ("computed", revision_id, "draft")]


def test_a_designation_registered_follows_the_reference_once_it_is_designated(
    api: ContractClient, stage: Scene
) -> None:
    # What EP-07 refreshes once a reference is designated — the budgeted amounts of the current
    # revision —, in the transaction of the designation, the revision designated already.
    followed: list[tuple[UUID, UUID, bool]] = []

    def follow(designation: ReferenceDesignated) -> None:
        designated = designation.session.scalar(
            select(Revision.is_reference).where(Revision.id == designation.revision_id)
        )
        followed.append((designation.project_id, designation.revision_id, bool(designated)))

    project_id = stage.project["project_id"]
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        give_a_line(session.connection(), give_a_task(session.connection(), revision_id))
        mark_revision(session, revision_id, "v1.0", None, Act(None, utc_now()))
    path = f"{PROJECTS}/{project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    with ExitStack() as registered:
        registered.callback(register_designation(follow))
        response = api.put(
            f"{path}/reference-revision",
            headers=stage.manager.headers,
            json={"revision_id": str(revision_id), "confirmed": True, "lock_version": counter},
        )
    assert response.status_code == 200, response.text
    assert followed == [(UUID(project_id), revision_id, True)]


def test_an_employment_registered_names_the_categories_a_line_employs(
    session: Session,
) -> None:
    # The categories each answer registered names, gathered; none while nothing is registered.
    first, second, third = uuid4(), uuid4(), uuid4()
    asked = [first, second, third]
    assert category_is_employed(session, asked) == frozenset()
    with ExitStack() as registered:
        registered.callback(register_employment(lambda _session, _ids: frozenset({first})))
        registered.callback(
            register_employment(lambda _session, ids: frozenset(ids) - {first, third})
        )
        assert category_is_employed(session, asked) == frozenset({first, second})


def test_the_end_of_a_merge_is_judged_once_after_every_part_whatever_their_order(
    api: ContractClient, stage: Scene
) -> None:
    # A tool of the registries, which covers no requirement: the parts of a merge, each in the order
    # of its registration, then its ends, called once after every part, even a part registered after
    # an end (#3946); the differences in the order of their change, each change in the order of the
    # parts, the completed tasks and the refusals in the order of the parts, the ends' after; the
    # merge on structures without a node, which the planning and the estimate find nothing of.
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision_id}/structures"
    opened = api.post(
        path, headers=stage.manager.headers, json={"kind": "amendment", "label": "Avenant"}
    )
    assert opened.status_code == 201, opened.text
    main = api.get(path, headers=stage.manager.headers).json()[0]
    asked: list[str] = []

    def part(name: str, change: str) -> Callable[[StructureMerging], MergePart]:
        def found(given: StructureMerging) -> MergePart:
            assert given.applying is False
            asked.append(name)
            return MergePart(
                differences=({"change": change, "target": name},),
                completed_tasks=({"lineage_id": name},),
                refusals=({"code": "LINK_CYCLE", "params": {"by": name}},),
            )

        return found

    with ExitStack() as registered, Session(stage.owner) as session:
        merging = StructureMerging(
            session,
            UUID(stage.project["project_id"]),
            revision_id,
            UUID(main["structure_id"]),
            UUID(opened.json()["structure_id"]),
            Act(None, utc_now()),
            applying=False,
        )
        assert merge_parts(merging) == MergePart()
        registered.callback(register_merge_end(part("end", "updated")))
        registered.callback(register_merge(part("task", "removed")))
        registered.callback(register_merge(part("estimate_line", "added")))
        found = merge_parts(merging)
    assert asked == ["task", "estimate_line", "end"]
    assert found == MergePart(
        differences=(
            {"change": "added", "target": "estimate_line"},
            {"change": "updated", "target": "end"},
            {"change": "removed", "target": "task"},
        ),
        completed_tasks=tuple({"lineage_id": name} for name in asked),
        refusals=tuple({"code": "LINK_CYCLE", "params": {"by": name}} for name in asked),
    )


def test_a_part_of_a_merge_with_a_change_unknown_is_a_defect_named_by_its_error(
    api: ContractClient, stage: Scene
) -> None:
    # A tool of the registries, which covers no requirement: a part that gives a change the report
    # does not know is a defect of the module that registered it (#3948), named by a
    # ``MergePartError`` and not by the index of the sort; withdrawn, the merge gives its parts.
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision_id}/structures"
    opened = api.post(
        path, headers=stage.manager.headers, json={"kind": "amendment", "label": "Avenant"}
    )
    assert opened.status_code == 201, opened.text
    main = api.get(path, headers=stage.manager.headers).json()[0]

    def faulty(_given: StructureMerging) -> MergePart:
        return MergePart(differences=({"change": "moved", "target": "task"},))

    with ExitStack() as registered, Session(stage.owner) as session:
        merging = StructureMerging(
            session,
            UUID(stage.project["project_id"]),
            revision_id,
            UUID(main["structure_id"]),
            UUID(opened.json()["structure_id"]),
            Act(None, utc_now()),
            applying=False,
        )
        withdraw = register_merge(faulty)
        registered.callback(withdraw)
        with pytest.raises(MergePartError, match="'moved'"):
            merge_parts(merging)
        registered.pop_all()  # disarms all `registered` holds (this one callback)
        withdraw()
        assert merge_parts(merging) == MergePart()
