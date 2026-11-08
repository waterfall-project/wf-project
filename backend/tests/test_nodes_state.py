# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the tasks under its state, its rights, its history and its revisions (US-1380/L2).

The writes of the tree refused on a marked revision, a terminal project, while a background task
runs, to who may not write; each write's entry of the history; the nodes deleted with an
abandoned revision and copied into the next one; two writes of one structure at once; the
calendar of a task, the default one or those a facet of a later module names (``register_facet``).
Every answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from nodes_support import (
    CHANGE,
    CONSULT,
    SESSION,
    Tree,
    entries,
    mark,
    opened,
    refusal,
    signed_in,
)
from planning_support import insert_link
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, select

from waterfall.core.history.tables import UndoEntry
from waterfall.core.planning.interface import FacetHooks, calendar_of, register_facet
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.resource_settings.interface import CalendarContent, WeeklyHours, create_calendar
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


# --- The state and the rights ------------------------------------------------------------------


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_marked_revision_reads_as_the_current_one_and_refuses_every_write(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Études")
    mark(stage, tree.revision)
    assert tree.labels() == ["Études"]
    refused = (tree.create("Revue"), tree.change(node, label="Autre"))
    for answer in refused:
        assert refusal(answer) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": "revision_draft"},
        )
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    for answer in (tree.create("Revue"), tree.change(node, label="Autre")):
        assert refusal(answer)[2] == {"missing_condition": "project_not_terminal"}
    assert tree.labels() == ["Études"]


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_write_while_a_background_task_runs_in_the_project_is_refused(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    node = tree.made("Études")
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    for answer in (tree.create("Revue"), tree.change(node, label="Autre")):
        assert refusal(answer) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": "no_background_task_running"},
        )


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_reader_an_outsider_and_a_contributor_without_planning_write_do_not_write(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    node = tree.made("Études")
    reading = person(stage.database, realm, "project_settings.read", CONSULT)
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(tree.create("Revue", reading)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": CHANGE},
    )
    # Who sees every project and may write the planning is still no contributor of this one.
    seeing = person(stage.database, realm, CONSULT, CHANGE, "all_projects_read")
    assert refusal(tree.create("Revue", seeing)) == (
        403,
        "NOT_CONTRIBUTOR",
        {"missing_condition": "is_contributor"},
    )
    assert tree.create("Revue", stage.reader).status_code == 403
    assert refusal(tree.change(node, stage.outsider, label="Autre"))[:2] == (404, "NOT_FOUND")
    assert tree.read(who=stage.outsider).status_code == 404
    assert tree.read(who=stage.reader).status_code == 200
    assert tree.create("Revue", stage.participant).status_code == 201
    assert tree.labels() == ["Études", "Revue"]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_structure_of_another_revision_or_unknown_is_not_found(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    moved = tree.path.replace(tree.revision["revision_id"], str(uuid4()))
    for path in (moved, f"{tree.path.rsplit('/', 1)[0]}/{uuid4()}"):
        answer = api.get(f"{path}/nodes", headers=stage.manager.headers)
        assert refusal(answer) == (404, "NOT_FOUND", {})


# --- The history, the abandonment, the copy, two writes at once ---------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_each_write_keeps_its_entry_with_the_nodes_before_and_after_it(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    writer = signed_in(stage, realm)
    created = tree.create("Études", writer)
    assert created.status_code == 201, created.text
    node = created.json()["nodes"][0]
    tree.changed({**node}, label="Études détaillées")  # the manager, without a session: no entry
    read = tree.node(node["node_id"])
    assert tree.change(read, writer, label="Avant-projet").status_code == 200
    kept = entries(stage)
    assert [(entry.kind, entry.rank, entry.session_id) for entry in kept] == [
        ("node_create", 1, SESSION),
        ("cell", 2, SESSION),
    ]
    creation, cell = kept
    assert creation.node_ids == [UUID(node["node_id"])]
    assert creation.before == []
    [after] = creation.after
    assert (after["object_id"], after["lock_version"], after["label"]) == (
        node["node_id"],
        1,
        "Études",
    )
    assert after["rows"]["task"]["label"] == "Études"
    assert after["rows"]["node"]["rank"] == 1
    assert (cell.before[0]["lock_version"], cell.after[0]["lock_version"]) == (2, 3)
    assert cell.before[0]["rows"]["task"]["label"] == "Études détaillées"
    assert cell.after[0]["rows"]["task"]["label"] == "Avant-projet"
    # A refused write keeps nothing.
    assert (
        tree.create(
            "Exploitation", writer, task={"duration": {"value": "200", "unit": "mo"}}
        ).status_code
        == 422
    )
    assert len(entries(stage)) == 2


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_abandonment_of_a_full_revision_leaves_no_node_no_facet_no_link(
    api: ContractClient, tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    writer = signed_in(stage, realm)
    studies = tree.made("Études")
    first = tree.made("Études de détail", parent_id=studies["node_id"])
    second = tree.create("Revue", writer, parent_id=studies["node_id"]).json()["nodes"][0]
    with stage.database.transaction() as session:
        session.execute(
            insert_link(
                UUID(stage.project["project_id"]),
                UUID(tree.revision["revision_id"]),
                UUID(tree.structure_id),
                UUID(first["node_id"]),
                UUID(second["node_id"]),
            )
        )
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    gone = api.delete(
        f"{path}?lock_version={revision['lock_version']}", headers=stage.manager.headers
    )
    assert gone.status_code == 204, gone.text
    with stage.database.transaction() as session:
        for table in (Node, Task, TaskLink, UndoEntry):
            assert session.scalar(select(func.count()).select_from(table)) == 0, table


@pytest.mark.requirement("WF-DAT-0010-A")
def test_a_revision_opened_from_a_marked_one_copies_its_tree_its_facets_and_its_links(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    studies = tree.made("Études")
    first = tree.made("Études de détail", parent_id=studies["node_id"])
    second = tree.made("Revue", parent_id=studies["node_id"])
    with stage.database.transaction() as session:
        session.execute(
            insert_link(
                UUID(stage.project["project_id"]),
                UUID(tree.revision["revision_id"]),
                UUID(tree.structure_id),
                UUID(first["node_id"]),
                UUID(second["node_id"]),
            )
        )
    before = tree.items()
    mark(stage, tree.revision)
    copy = Tree(api, stage, opened(api, stage))
    after = copy.items()
    assert [item["lineage_id"] for item in after] == [item["lineage_id"] for item in before]
    assert {item["node_id"] for item in after}.isdisjoint({item["node_id"] for item in before})
    assert [item["task"]["label"] for item in after] == ["Études", "Études de détail", "Revue"]
    assert [item["lock_version"] for item in after] == [1, 1, 1]
    assert after[2]["predecessors"][0]["predecessor_node_id"] == after[1]["node_id"]
    assert after[2]["task"]["start"] == before[2]["task"]["start"]
    # The marked revision keeps its own, unchanged.
    assert tree.items() == before


@pytest.mark.requirement("WF-PLA-0080-A")
def test_two_creations_at_once_in_one_structure_are_both_written_one_after_the_other(
    tree: Tree,
) -> None:
    with ThreadPoolExecutor(2) as pool:
        pending = [pool.submit(tree.create, label) for label in ("Gauche", "Droite")]
        answers = [each.result() for each in pending]
    assert [answer.status_code for answer in answers] == [201, 201]
    counters = sorted(answer.json()["structure_lock_version"] for answer in answers)
    assert counters[1] == counters[0] + 1
    read = tree.items()
    assert sorted(item["task"]["label"] for item in read) == ["Droite", "Gauche"]
    assert [item["position"] for item in read] == [1, 2]
    with tree.stage.database.transaction() as session:
        ranks = session.scalars(select(Node.rank).order_by(Node.rank)).all()
    assert ranks == [1, 2]
    assert Decimal(read[0]["task"]["duration"]["value"]) == 1


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_reading_made_while_tasks_are_created_answers_a_consistent_state_every_time(
    tree: Tree, stage: Scene
) -> None:
    project_id = UUID(stage.project["project_id"])
    revision_id, structure_id = UUID(tree.revision["revision_id"]), UUID(tree.structure_id)
    first = tree.made("Départ")
    finished = []

    def writing() -> None:
        previous = first
        for index in range(12):
            node = tree.made(f"Tâche {index}")
            with stage.database.transaction() as session:
                session.execute(
                    insert_link(
                        project_id,
                        revision_id,
                        structure_id,
                        UUID(previous["node_id"]),
                        UUID(node["node_id"]),
                    )
                )
            previous = node
        finished.append(True)

    def reading() -> list[int]:
        found: list[int] = []
        while not finished:
            for answer in (
                tree.read(),
                tree.api.get(
                    f"{tree.path}/nodes/{first['node_id']}/dependencies?field=task.start",
                    headers=stage.manager.headers,
                ),
                tree.api.get(f"{tree.path}/rows/1", headers=stage.manager.headers),
            ):
                found.append(answer.status_code)
        return found

    with ThreadPoolExecutor(3) as pool:
        written = pool.submit(writing)
        readers = [pool.submit(reading) for _ in range(2)]
        written.result()
        statuses = [status for each in readers for status in each.result()]
    assert statuses
    assert set(statuses) == {200}
    assert len(tree.items()) == 13


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_is_on_the_default_calendar_or_on_the_calendars_its_facets_name_intersected(
    tree: Tree, stage: Scene
) -> None:
    # « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. » The
    # calendars of the roles of its lines are EP-07's, which names them by its facet
    # (``register_facet``); a facet of a test names them here, and the task is placed on the
    # fewest hours of each day, a calendar of no identifier.
    node = tree.made("Câblage")
    project_id, task_id = UUID(stage.project["project_id"]), UUID(node["node_id"])
    week = (Decimal(6), Decimal(8), Decimal(8), Decimal(8), Decimal(4), Decimal(0), Decimal(0))
    with stage.database.transaction() as session:
        content = CalendarContent("Atelier", WeeklyHours(*week))
        short = create_calendar(session, content, Act(None, utc_now())).calendar_id
        default = calendar_of(session, project_id, task_id)
    assert default.calendar_id == UUID(node["task"]["calendar_id"])
    assert default.calendar.week == (*[Decimal(8)] * 5, Decimal(0), Decimal(0))
    named: set[UUID] = {short}

    def calendars(session: Session, project: UUID, task: UUID) -> set[UUID]:
        del session
        return named if (project, task) == (project_id, task_id) else set()

    def read(*_: object) -> dict[UUID, object]:
        return {}

    def nothing(*_: object) -> None:
        return None

    hooks = FacetHooks(read, nothing, nothing, calendars)
    withdraw = register_facet("estimate_line", hooks)
    try:
        with pytest.raises(ValueError, match="registered already"):
            register_facet("estimate_line", hooks)
        with stage.database.transaction() as session:
            own = calendar_of(session, project_id, task_id)
            named.add(default.calendar_id or short)
            both = calendar_of(session, project_id, task_id)
    finally:
        withdraw()
    assert (own.calendar_id, own.calendar.week) == (short, week)
    assert (both.calendar_id, both.calendar.week) == (None, week)
