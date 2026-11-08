# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the tasks: deleted and moved (US-1380/L3).

``deleteNode`` and ``moveNodes`` on the main structure of a revision a project's manager opened,
every answer checked against the contract: a subtree deleted with its links and the inscriptions
of its lineages, a started task kept; a selection moved with its subtrees, placed by kind after
the sibling named, its former and new ancestors given back; a summary left without subordinate
made a leaf in its state; the refusals of the tree, of the links through the hierarchy and of the
horizon, nothing written; each write's entry of the history, two moves at one counter. The links,
the states and the inscriptions their stories write are written around the service.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import (
    Tree,
    entries,
    faults,
    opened,
    refusal,
    scheduled_at,
    set_progress,
    signed_in,
)
from planning_support import DAY, insert_link
from project_rows import STAMP
from projects_support import scene as make_scene
from sqlalchemy import Engine, event, func, insert, select

from waterfall.core.planning.interface import structures
from waterfall.core.planning.tables import Node, TaskLink, TrackingEntry
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def delete(tree: Tree, node: dict[str, Any], who: Person | None = None) -> Any:
    """Delete a node at the counter read, as the manager does by default; give the answer."""
    headers = (who or tree.stage.manager).headers
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    return tree.api.delete(path, headers=headers)


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def move(
    tree: Tree, nodes: list[dict[str, Any]], parent: dict[str, Any] | None, **body: Any
) -> Any:
    """Move nodes under a parent at the counter of the structure read; give the answer."""
    who = body.pop("who", None)
    sent = {
        "node_ids": [node["node_id"] for node in nodes],
        "parent_id": None if parent is None else parent["node_id"],
        "lock_version": counter(tree),
        **body,
    }
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/move", headers=headers, json=sent)


def moved(
    tree: Tree, nodes: list[dict[str, Any]], parent: dict[str, Any] | None, **body: Any
) -> Any:
    """Move nodes that must move; give what is answered."""
    answer = move(tree, nodes, parent, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def link(tree: Tree, predecessor: dict[str, Any], successor: dict[str, Any]) -> None:
    """Link two tasks finish to start around the service, as US-1390 will."""
    project_id, revision_id = tree.stage.project["project_id"], tree.revision["revision_id"]
    with tree.stage.owner.begin() as connection:
        connection.execute(
            insert_link(
                UUID(project_id),
                UUID(revision_id),
                UUID(tree.structure_id),
                UUID(predecessor["node_id"]),
                UUID(successor["node_id"]),
            )
        )


def by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Give nodes by their identifier."""
    return {item["node_id"]: item for item in items}


def facet(node: dict[str, Any]) -> dict[str, Any]:
    """Give what a move leaves of a task: all but its parent, its place, its number."""
    held = {k: v for k, v in node.items() if k not in {"parent_id", "position", "row_number"}}
    return {**held, "predecessors": None}


# --- Deletion ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0070-A")
def test_a_summary_deleted_takes_its_subtree_its_links_and_inscriptions_and_redates(
    tree: Tree, stage: Scene
) -> None:
    # « La suppression d'une récapitulative supprime ses subordonnées et leurs lignes » : the
    # lines are EP-07's; the subtree, its links and the inscriptions of its lineages go.
    project = tree.made("Projet")
    studies = tree.made("Études", parent_id=project["node_id"])
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    tree.made("Note de calcul", parent_id=detail["node_id"])
    works = tree.made("Travaux", parent_id=project["node_id"])
    link(tree, detail, works)
    # A write after the link dates the works after the detailed studies.
    tree.changed(tree.node(works["node_id"]), description="Lot unique")
    assert tree.node(works["node_id"])["task"]["start"]["date"] != DAY.isoformat()
    with stage.database.transaction() as session:
        session.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                project_id=UUID(stage.project["project_id"]),
                lineage_id=UUID(detail["lineage_id"]),
                kind="milestone_tracking",
                timeline_id=None,
                **STAMP,
            )
        )
    before = counter(tree)
    answer = delete(tree, tree.node(studies["node_id"]))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["nodes"] == []
    assert [each["node_id"] for each in body["ancestors"]] == [project["node_id"]]
    # The link taken away leaves the works free to start with the planning.
    assert [each["node_id"] for each in body["rescheduled"]] == [works["node_id"]]
    assert body["rescheduled"][0]["start"] == {"date": DAY.isoformat(), "hours": "0"}
    assert body["totals"]["task_count"] == 2
    assert body["structure_lock_version"] == before + 1
    assert tree.labels() == ["Projet", "Travaux"]
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(TaskLink)) == 0
        assert session.scalar(select(func.count()).select_from(TrackingEntry)) == 0


@pytest.mark.requirement("WF-PLA-0070-A")
def test_a_started_or_completed_task_and_a_summary_over_one_are_not_deleted(
    tree: Tree, stage: Scene
) -> None:
    # « La suppression d'une tâche démarrée est refusée » : the screen sends back to the remaining
    # to commit, EP-09's.
    studies = tree.made("Études")
    started = tree.made("Relevés", parent_id=studies["node_id"])
    done = tree.made("Plans")
    set_progress(stage, started["node_id"], "started", DAY)
    set_progress(stage, done["node_id"], "completed", DAY)
    for node in (started, studies, done):
        answer = delete(tree, tree.node(node["node_id"]))
        assert refusal(answer) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": "task_not_started"},
        )
    assert tree.labels() == ["Études", "Relevés", "Plans"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_deletion_at_a_stale_version_or_of_an_unknown_node_deletes_nothing(tree: Tree) -> None:
    node = tree.made("Études")
    tree.changed(node, label="Études détaillées")
    assert refusal(delete(tree, node)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": 2},
    )
    assert refusal(delete(tree, {**node, "node_id": str(uuid4())}))[:2] == (404, "NOT_FOUND")
    assert tree.labels() == ["Études détaillées"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_the_only_subordinate_of_a_summary_of_ten_days_deleted_leaves_a_leaf_of_ten_days(
    tree: Tree,
) -> None:
    # « La suppression de la seule subordonnée d'une récapitulative de dix jours laisse une tâche
    # feuille de dix jours, à laquelle une sous-tâche peut de nouveau être ajoutée. »
    summary = tree.made("Études")
    only = tree.made(
        "Note de calcul",
        parent_id=summary["node_id"],
        task={"duration": {"value": "2", "unit": "w"}},
    )
    assert tree.node(summary["node_id"])["task"]["duration"] == {"value": "10", "unit": "d"}
    body = delete(tree, tree.node(only["node_id"])).json()
    leaf = body["ancestors"][0]
    assert leaf["node_id"] == summary["node_id"]
    assert leaf["task"]["is_summary"] is False
    assert leaf["task"]["is_milestone"] is False
    assert leaf["task"]["duration"] == {"value": "10", "unit": "d"}
    assert leaf["task"]["scheduling_mode"] == "automatic"
    assert "task.duration" in leaf["editable_fields"]
    assert leaf["computed_fields"] == ["task.start", "task.finish"]
    assert leaf["lock_version"] == summary["lock_version"] + 1
    again = tree.create("Relevés", parent_id=summary["node_id"])
    assert again.status_code == 201, again.text


@pytest.mark.requirement("WF-PLA-0040-A")
def test_the_only_milestone_of_a_summary_deleted_leaves_a_milestone_not_started(
    tree: Tree,
) -> None:
    # « … Si cette durée est nulle, elle devient un jalon, à l'état non démarré. »
    summary = tree.made("Réception")
    only = tree.made("Procès-verbal", parent_id=summary["node_id"], task=MILESTONE)
    body = delete(tree, tree.node(only["node_id"])).json()
    task = body["ancestors"][0]["task"]
    assert (task["is_summary"], task["is_milestone"]) == (False, True)
    assert (task["progress"], task["duration"]) == ("not_started", {"value": "0", "unit": "d"})


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_summary_left_a_leaf_by_a_deletion_is_refused_at_the_counter_read_before(
    tree: Tree,
) -> None:
    # The summary written (it became a leaf) advances its counter: a facet change at the counter
    # read before the deletion is refused.
    summary = tree.made("Études")
    only = tree.made("Note", parent_id=summary["node_id"])
    before = tree.node(summary["node_id"])
    assert delete(tree, tree.node(only["node_id"])).status_code == 200
    answer = tree.change(before, label="Études détaillées")
    assert refusal(answer) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": before["lock_version"] + 1},
    )


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_summary_left_a_leaf_by_a_move_is_refused_at_the_counter_read_before(
    tree: Tree,
) -> None:
    summary = tree.made("Études")
    only = tree.made("Note", parent_id=summary["node_id"])
    before = tree.node(summary["node_id"])
    moved(tree, [tree.node(only["node_id"])], None)
    answer = tree.change(before, label="Études détaillées")
    assert refusal(answer)[:2] == (412, "STALE_LOCK_VERSION")


# --- Move --------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_moved_takes_its_two_levels_unchanged_and_gives_its_ancestors_back(
    tree: Tree,
) -> None:
    # « Après déplacement d'une récapitulative portant deux niveaux de subordonnées, les tâches et
    # les lignes déplacées sont inchangées » : the lines and the estimate are EP-07's.
    origin = tree.made("Études")
    tree.made("Revue", parent_id=origin["node_id"])
    summary = tree.made("Câblage", parent_id=origin["node_id"])
    level = tree.made("Armoires", parent_id=summary["node_id"])
    tree.made("Borniers", parent_id=level["node_id"])
    target = tree.made("Chantier")
    tree.made("Livraison", parent_id=target["node_id"])
    below = [item for item in tree.items() if item["node_id"] != summary["node_id"]]
    subtree = {item["node_id"]: item for item in tree.items(f"?subtree_of={summary['node_id']}")}
    body = moved(tree, [tree.node(summary["node_id"])], target)
    node = body["nodes"][0]
    assert (node["parent_id"], node["position"], node["level"]) == (target["node_id"], 2, 2)
    assert node["lock_version"] == summary["lock_version"] + 1
    assert [each["node_id"] for each in body["ancestors"]] == [
        origin["node_id"],
        target["node_id"],
    ]
    assert tree.labels() == [
        "Études",
        "Revue",
        "Chantier",
        "Livraison",
        "Câblage",
        "Armoires",
        "Borniers",
    ]
    after = by_id(tree.items())
    for node_id, item in subtree.items():
        if node_id != summary["node_id"]:
            assert facet(after[node_id]) == facet(item)
    assert all(after[item["node_id"]]["lock_version"] == item["lock_version"] for item in below)


@pytest.mark.requirement("WF-PLA-0040-A")
def test_the_only_milestone_of_a_completed_summary_moved_leaves_a_completed_milestone(
    tree: Tree, stage: Scene
) -> None:
    # « Une récapitulative terminée dont la seule subordonnée, un jalon, est déplacée devient un
    # jalon terminé. »
    summary = tree.made("Réception")
    milestone = tree.made("Procès-verbal", parent_id=summary["node_id"], task=MILESTONE)
    set_progress(stage, milestone["node_id"], "completed", DAY)
    body = moved(tree, [tree.node(milestone["node_id"])], None)
    left = body["ancestors"][0]
    assert left["node_id"] == summary["node_id"]
    task = left["task"]
    assert (task["is_summary"], task["is_milestone"]) == (False, True)
    assert (task["progress"], task["completed_on"]) == ("completed", DAY.isoformat())
    assert task["duration"] == {"value": "0", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_started_summary_of_nought_duration_left_without_subordinate_is_a_leaf_of_a_day(
    tree: Tree, stage: Scene
) -> None:
    # « … privée de ce jalon, est une feuille démarrée d'un jour, non un jalon » : the own line
    # that keeps it started is EP-07's; started by its two milestones, one completed.
    summary = tree.made("Réception")
    first = tree.made("Procès-verbal", parent_id=summary["node_id"], task=MILESTONE)
    second = tree.made("Levée des réserves", parent_id=summary["node_id"], task=MILESTONE)
    set_progress(stage, first["node_id"], "completed", DAY)
    read = tree.node(summary["node_id"])["task"]
    assert (read["progress"], read["duration"]) == ("started", {"value": "0", "unit": "d"})
    body = moved(tree, [tree.node(first["node_id"]), tree.node(second["node_id"])], None)
    task = by_id(body["ancestors"])[summary["node_id"]]["task"]
    assert (task["is_summary"], task["is_milestone"]) == (False, False)
    assert (task["progress"], task["started_on"]) == ("started", DAY.isoformat())
    assert task["duration"] == {"value": "1", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_task_moved_under_a_milestone_is_refused_and_nothing_moves(tree: Tree) -> None:
    # « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. » (#1772)
    milestone = tree.made("Réception usine", task=MILESTONE)
    task = tree.made("Mise en service")
    answer = move(tree, [task], milestone)
    assert faults(answer) == [
        (
            "/parent_id",
            "MILESTONE_HAS_NO_SUBTASK",
            {"node_id": milestone["node_id"], "label": "Réception usine"},
        )
    ]
    assert tree.node(task["node_id"])["parent_id"] is None


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_move_that_takes_the_project_beyond_fifteen_years_is_refused_naming_the_task(
    tree: Tree,
) -> None:
    # « Le déplacement d'une tâche qui porterait la fin du projet à quinze ans et un jour de son
    # début est refusé, et la tâche est nommée. » : each lasts some eight years; the summary
    # follows the first, and covers the second once it is moved under it.
    long = {"duration": {"value": "3000", "unit": "ed"}}
    first = tree.made("Exploitation", task=long)
    summary = tree.made("Maintenance")
    tree.made("Visite", parent_id=summary["node_id"])
    second = tree.made("Garantie", task=long)
    link(tree, first, summary)
    before = counter(tree)
    answer = move(tree, [second], summary)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": second["node_id"], "label": "Garantie"}},
    )
    assert tree.node(second["node_id"])["parent_id"] is None
    assert counter(tree) == before


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_move_that_links_a_summary_to_its_subordinate_or_closes_a_loop_is_refused(
    tree: Tree,
) -> None:
    # « La création d'une liaison fermant un cycle, ou reliant une récapitulative à l'une de ses
    # subordonnées, est refusée, et la raison en est nommée à l'utilisateur. » — by a move (#1169).
    preparation = tree.made("Préparation")
    realisation = tree.made("Réalisation")
    documentation = tree.made("Documentation")
    link(tree, preparation, realisation)
    link(tree, realisation, documentation)
    indented = move(tree, [realisation], preparation)
    assert refusal(indented) == (422, "LINK_FORBIDDEN", {})
    looped = move(tree, [documentation], preparation)
    assert refusal(looped) == (
        422,
        "LINK_CYCLE",
        {
            "cycle": [
                {"node_id": each["node_id"], "label": each["task"]["label"]}
                for each in (preparation, realisation, documentation)
            ]
        },
    )
    assert [item["level"] for item in tree.items()] == [1, 1, 1]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_selection_is_placed_in_its_order_after_the_sibling_named_or_at_the_ends(
    tree: Tree,
) -> None:
    parent = tree.made("Chantier")
    first = tree.made("Premier", parent_id=parent["node_id"])
    tree.made("Dernier", parent_id=parent["node_id"])
    one, two = tree.made("Un"), tree.made("Deux")
    moved(
        tree,
        [tree.node(two["node_id"]), tree.node(one["node_id"])],
        parent,
        after_node_id=first["node_id"],
    )
    assert tree.labels() == ["Chantier", "Premier", "Deux", "Un", "Dernier"]
    head = tree.made("Tête")
    moved(tree, [tree.node(head["node_id"])], parent, after_node_id=None)
    assert tree.labels(f"?subtree_of={parent['node_id']}")[1] == "Tête"
    tail = tree.made("Queue")
    body = moved(tree, [tree.node(tail["node_id"])], parent)
    assert body["nodes"][0]["position"] == 6
    assert [item["position"] for item in tree.items()[1:]] == [1, 2, 3, 4, 5, 6]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_place_after_a_node_that_is_no_sibling_is_refused_and_nothing_moves(tree: Tree) -> None:
    # No Vérif of the spec states the refusal; the move that carries the subordinates is the
    # closest, and the contract (``NODE_NOT_SIBLING``) the rule.
    parent = tree.made("Chantier")
    inner = tree.made("Câblage", parent_id=parent["node_id"])
    other = tree.made("Études")
    for after in (inner["node_id"], other["node_id"], str(uuid4())):
        answer = move(tree, [other], None, after_node_id=after)
        assert faults(answer) == [("/after_node_id", "NODE_NOT_SIBLING", {})]
    assert tree.labels() == ["Chantier", "Câblage", "Études"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_selection_moved_under_itself_or_one_of_its_subordinates_closes_a_loop_refused(
    tree: Tree,
) -> None:
    # A summary moved takes its subordinates with it: under one of them, or under itself, the
    # hierarchy would loop, and the refusal says so (``NODE_CYCLE``, #2500).
    parent = tree.made("Chantier")
    inner = tree.made("Câblage", parent_id=parent["node_id"])
    for target in (inner, parent):
        answer = move(tree, [parent], target)
        assert faults(answer) == [("/parent_id", "NODE_CYCLE", {})]
    assert tree.labels() == ["Chantier", "Câblage"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_selection_moved_under_an_unknown_parent_is_refused_as_an_unknown_task(
    tree: Tree,
) -> None:
    # A parent the structure does not hold as a task: ``UNKNOWN_TASK`` on its field (#2500).
    parent = tree.made("Chantier")
    answer = move(tree, [parent], {"node_id": str(uuid4())})
    assert faults(answer) == [("/parent_id", "UNKNOWN_TASK", {})]
    assert tree.labels() == ["Chantier"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_selection_of_an_unknown_node_is_not_found(tree: Tree) -> None:
    tree.made("Chantier")
    assert refusal(move(tree, [{"node_id": str(uuid4())}], None))[:2] == (404, "NOT_FOUND")
    assert tree.labels() == ["Chantier"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_two_moves_at_one_counter_move_once_and_the_other_is_refused_stale(tree: Tree) -> None:
    parent = tree.made("Chantier")
    task = tree.made("Câblage")
    sent = {
        "node_ids": [task["node_id"]],
        "parent_id": parent["node_id"],
        "lock_version": counter(tree),
    }

    def asked(_: int) -> int:
        path = f"{tree.path}/nodes/move"
        return tree.api.post(path, headers=tree.stage.manager.headers, json=sent).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(asked, range(2)))
    assert statuses == [200, 412]
    assert tree.node(task["node_id"])["parent_id"] == parent["node_id"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_deletion_and_a_move_keep_their_entry_of_the_history(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    who = signed_in(stage, realm)
    parent = tree.made("Chantier", who=who)
    task = tree.made("Câblage", who=who)
    moved(tree, [task], parent, who=who)
    assert delete(tree, tree.node(task["node_id"]), who).status_code == 200
    kinds = [(entry.kind, entry.node_ids) for entry in entries(stage)]
    assert kinds[-2:] == [
        ("node_move", [UUID(task["node_id"])]),
        ("node_delete", [UUID(task["node_id"])]),
    ]
    # The summary the deletion leaves bare is kept with it, as it was and as it becomes.
    [deleting] = [entry for entry in entries(stage) if entry.kind == "node_delete"]
    assert [each["object_id"] for each in deleting.before] == [task["node_id"], parent["node_id"]]
    assert [each["object_id"] for each in deleting.after] == [parent["node_id"]]
    with stage.database.transaction() as session:
        count = session.scalar(select(func.count()).select_from(Node))
    assert count == 1


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_selection_of_a_summary_and_its_subordinate_moves_the_group_whole(tree: Tree) -> None:
    # « Le déplacement d'une sélection qui contient une récapitulative et l'une de ses subordonnées
    # laisse la subordonnée sous la récapitulative : le groupe est déplacé entier, sans être
    # aplati. » : the subordinate named is left to its summary, whatever the order sent (#2507).
    target = tree.made("Chantier")
    summary = tree.made("Études")
    child = tree.made("Note", parent_id=summary["node_id"])
    grandchild = tree.made("Annexe", parent_id=child["node_id"])
    sent = [tree.node(each["node_id"]) for each in (grandchild, summary, child)]
    body = moved(tree, sent, target)
    assert [node["node_id"] for node in body["nodes"]] == [summary["node_id"]]
    assert [(i["task"]["label"], i["level"]) for i in tree.items()] == [
        ("Chantier", 1),
        ("Études", 2),
        ("Note", 3),
        ("Annexe", 4),
    ]
    assert tree.node(child["node_id"])["parent_id"] == summary["node_id"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_write_of_the_tree_reads_the_facts_of_its_structure_once(
    tree: Tree, request: pytest.FixtureRequest
) -> None:
    # #2492: the facts of the structure, read under its lock, are handed to the replay; a second
    # reading under the lock would lock the structure again.
    calls: list[int] = []

    # Counted at the database, whichever module asks: a name imported elsewhere and reading the
    # facts again under the lock would be missed by a patch of a function.
    def counted(_conn: Any, _cursor: Any, statement: str, *_rest: Any) -> None:
        text = " ".join(statement.lower().split())
        if "from cost_structure" in text and " for update" in text:
            calls.append(1)

    event.listen(Engine, "before_cursor_execute", counted)
    request.addfinalizer(lambda: event.remove(Engine, "before_cursor_execute", counted))
    summary = tree.made("Études")
    assert len(calls) == 1
    calls.clear()
    note = tree.made("Note", parent_id=summary["node_id"])
    assert len(calls) == 1
    calls.clear()
    moved(tree, [tree.node(note["node_id"])], None)
    assert len(calls) == 1
    calls.clear()
    deleted = delete(tree, tree.node(note["node_id"]))
    assert deleted.status_code == 200, deleted.text
    assert len(calls) == 1
    # The write of the structure itself builds the structure after from what it read (#2513).
    calls.clear()
    sent = {"label": "Autre", "lock_version": deleted.json()["structure_lock_version"]}
    answer = tree.api.patch(tree.path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    assert len(calls) == 1

    # A caller that has read nothing hands the replay no facts: it reads them, once, under the lock.
    calls.clear()
    with tree.stage.database.transaction() as session:
        structures.reschedule(
            session,
            UUID(tree.stage.project["project_id"]),
            UUID(tree.structure_id),
            scheduled_at(tree),
        )
    assert len(calls) == 1
