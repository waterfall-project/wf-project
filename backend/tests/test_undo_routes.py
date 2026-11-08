# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The routes of the history: ``undoLastChange`` and ``redoLastUndo`` (US-1450/L2).

Every answer checked against the contract, on the main structure of a revision a project's manager
opened, written by a contributor whose token carries a session of sign-in (``sid``) — the history
is kept per session. A deletion undone gives back its task, its links and its inscriptions; fifty
changes undone one by one and redone in order; a change another contributor took up since refused,
the object named; the refusals of the state, of the permission and of a token without a session;
the lock of the structure the entry names, found from the objects of an undoing and of a redoing;
the places, the parents and the elements of the work breakdown that others hold since.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from history_support import counter, delete, inscribe, link, redo, redone, undo, undone
from nodes_support import (
    SESSION,
    Tree,
    entries,
    mark,
    opened,
    refusal,
    signed_in,
    work_breakdown,
)
from project_rows import STAMP
from projects_support import put_in_state
from projects_support import scene as make_scene
from sqlalchemy import delete as delete_rows
from sqlalchemy import func, insert, select, update

from waterfall.core.history.interface import RecordedChange, UndoStack, recording
from waterfall.core.planning import writing
from waterfall.core.planning.interface import snapshot, undo_last_change
from waterfall.core.planning.tables import (
    Node,
    Task,
    TaskLink,
    Timeline,
    TrackingEntry,
)
from waterfall.core.projects.tables import WorkPackage
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ForbiddenError

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from sqlalchemy import Engine
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


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def rows(stage: Scene, table: Any) -> int:
    """Count the rows of a table the base keeps."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(table)) or 0


# --- The deletion of a task, undone --------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_deletion_of_a_task_then_its_undoing_give_back_the_task_its_links_and_inscriptions(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « La suppression d'une tâche puis son annulation restituent la tâche, ses lignes et
    # ses liaisons. » : les lignes sont d'EP-07 ; la tâche, ses liaisons, ses inscriptions ici.
    design = tree.made("Étude", who=who)
    works = tree.made("Travaux", who=who)
    test = tree.made("Essais", who=who)
    assert link(tree, tree.node(works["node_id"]), who, design).status_code == 200
    assert link(tree, tree.node(test["node_id"]), who, works).status_code == 200
    inscribe(stage, works["lineage_id"])
    before = tree.node(works["node_id"])
    dates = {each["node_id"]: each["task"]["start"] for each in tree.items()}

    deleted = delete(tree, before, who)
    assert deleted.status_code == 200, deleted.text
    assert tree.labels() == ["Étude", "Essais"]
    assert rows(stage, TaskLink) == 0
    assert rows(stage, TrackingEntry) == 0

    answer = undo(tree, who)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["undone"] == {"kind": "node_delete", "node_ids": [works["node_id"]], "risk_ids": []}
    assert body["remaining_depth"] == 5
    assert [each["node_id"] for each in body["written"]["nodes"]] == [works["node_id"]]
    # The task is back at its place with its facet, its predecessors and its inscription.
    assert tree.labels() == ["Étude", "Travaux", "Essais"]
    read = tree.node(works["node_id"])
    assert read["task"]["label"] == "Travaux"
    assert [each["predecessor_node_id"] for each in read["predecessors"]] == [design["node_id"]]
    assert [each["predecessor_node_id"] for each in tree.node(test["node_id"])["predecessors"]] == [
        works["node_id"]
    ]
    assert read["task"]["tracking"] == [{"kind": "milestone_tracking", "timeline_id": None}]
    assert {each["node_id"]: each["task"]["start"] for each in tree.items()} == dates
    assert read["lock_version"] == before["lock_version"] + 1
    assert body["written"]["structure_lock_version"] == counter(tree)

    # Redone, the deletion is made again, its links and inscription with the task.
    again = redone(tree, who)
    assert again["undone"]["kind"] == "node_delete"
    assert (again["remaining_depth"], again["written"]["nodes"]) == (0, [])
    assert tree.labels() == ["Étude", "Essais"]
    assert rows(stage, TaskLink) == 0
    assert rows(stage, TrackingEntry) == 0


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_deletion_gives_back_the_subtree_in_its_place_and_the_summary_it_left_bare(
    tree: Tree, who: Person
) -> None:
    # The deletion of the last subordinate makes its summary a leaf; its undoing makes it a
    # summary again, the subtree back under it, each task at its counter and rank.
    summary = tree.made("Étude", who=who)
    task = tree.made("Note", who=who, parent_id=summary["node_id"])
    sibling = tree.made("Revue", who=who)
    assert delete(tree, tree.node(task["node_id"]), who).status_code == 200
    assert tree.node(summary["node_id"])["task"]["is_summary"] is False
    body = undone(tree, who)
    assert body["undone"]["node_ids"] == [task["node_id"]]
    assert tree.labels() == ["Étude", "Note", "Revue"]
    assert tree.node(summary["node_id"])["task"]["is_summary"] is True
    assert tree.node(task["node_id"])["parent_id"] == summary["node_id"]
    assert tree.node(sibling["node_id"])["position"] == 2
    # Both are written back: the task, and the summary the deletion had made a leaf.
    assert [each["node_id"] for each in body["written"]["nodes"]] == [
        summary["node_id"],
        task["node_id"],
    ]
    assert body["written"]["ancestors"] == []


# --- The changes undone and redone --------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_fifty_changes_are_undone_one_by_one_then_redone_in_order(tree: Tree, who: Person) -> None:
    # Vérif : « Cinquante modifications successives s'annulent une par une, puis se rétablissent
    # dans l'ordre. » : contre le service, par l'API.
    task = tree.made("Libellé 0", who=who)
    for number in range(1, 51):
        node = tree.node(task["node_id"])
        assert tree.change(node, who, label=f"Libellé {number}").status_code == 200
    assert tree.labels() == ["Libellé 50"]
    for step in range(50):
        body = undone(tree, who)
        assert body["undone"] == {"kind": "cell", "node_ids": [task["node_id"]], "risk_ids": []}
        assert body["remaining_depth"] == 50 - step
        assert tree.labels() == [f"Libellé {49 - step}"]
    for step in range(50):
        body = redone(tree, who)
        assert body["undone"]["kind"] == "cell"
        assert body["remaining_depth"] == 49 - step
        assert tree.labels() == [f"Libellé {step + 1}"]
    assert redo(tree, who).status_code == 409


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undoing_is_a_write_like_any_other_it_advances_the_counters_and_the_audit_columns(
    tree: Tree, stage: Scene, who: Person
) -> None:
    task = tree.made("Câblage", who=who)
    assert tree.change(tree.node(task["node_id"]), who, label="Câblage du poste").status_code == 200
    node, structure = tree.node(task["node_id"]), counter(tree)
    body = undone(tree, who)
    assert body["written"]["structure_lock_version"] == structure + 1
    restored = tree.node(task["node_id"])
    assert restored["task"]["label"] == "Câblage"
    assert restored["lock_version"] == node["lock_version"] + 1
    with stage.database.transaction() as session:
        updated_by = session.scalar(select(Node.updated_by).where(Node.id == UUID(task["node_id"])))
    assert updated_by == who.user_id


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_predecessors_a_task_was_given_are_taken_away_by_the_undoing_and_given_again(
    tree: Tree, stage: Scene, who: Person
) -> None:
    design = tree.made("Étude", who=who)
    works = tree.made("Travaux", who=who)
    assert link(tree, tree.node(works["node_id"]), who, design).status_code == 200
    assert undone(tree, who)["undone"]["kind"] == "link"
    assert tree.node(works["node_id"])["predecessors"] == []
    assert rows(stage, TaskLink) == 0
    assert redone(tree, who)["undone"]["kind"] == "link"
    [predecessor] = tree.node(works["node_id"])["predecessors"]
    assert predecessor["predecessor_node_id"] == design["node_id"]
    assert rows(stage, TaskLink) == 1


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_creation_deletes_the_task_and_its_redoing_creates_it_again(
    tree: Tree, who: Person
) -> None:
    kept = tree.made("Étude", who=who)
    created = tree.made("Travaux", who=who)
    body = undone(tree, who)
    assert (body["undone"]["kind"], body["undone"]["node_ids"]) == (
        "node_create",
        [created["node_id"]],
    )
    assert body["written"]["nodes"] == []
    assert tree.labels() == ["Étude"]
    assert body["written"]["totals"]["task_count"] == 1
    again = redone(tree, who)
    assert [each["node_id"] for each in again["written"]["nodes"]] == [created["node_id"]]
    assert tree.labels() == ["Étude", "Travaux"]
    assert tree.node(kept["node_id"])["task"]["label"] == "Étude"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_move_brings_the_nodes_back_under_their_parent_and_in_their_place(
    tree: Tree, who: Person
) -> None:
    chantier = tree.made("Chantier", who=who)
    first = tree.made("Câblage", who=who)
    second = tree.made("Essais", who=who)
    sent = {"node_ids": [first["node_id"]], "parent_id": chantier["node_id"]}
    body = {**sent, "lock_version": counter(tree)}
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=who.headers, json=body)
    assert answer.status_code == 200, answer.text
    assert tree.node(first["node_id"])["parent_id"] == chantier["node_id"]
    assert undone(tree, who)["undone"]["kind"] == "node_move"
    assert [(each["task"]["label"], each["level"]) for each in tree.items()] == [
        ("Chantier", 1),
        ("Câblage", 1),
        ("Essais", 1),
    ]
    assert tree.node(second["node_id"])["position"] == 3
    assert redone(tree, who)["undone"]["kind"] == "node_move"
    assert tree.node(first["node_id"])["parent_id"] == chantier["node_id"]
    assert tree.labels() == ["Chantier", "Câblage", "Essais"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_start_date_brings_back_the_start_and_the_label_of_the_structure(
    tree: Tree, who: Person
) -> None:
    task = tree.made("Câblage", who=who)
    start = tree.node(task["node_id"])["task"]["start"]
    listed = tree.api.get(tree.path.rsplit("/", 1)[0], headers=who.headers).json()
    structure = next(each for each in listed if each["structure_id"] == tree.structure_id)
    sent = {
        "lock_version": structure["lock_version"],
        "planning_start_on": "2026-11-09",
        "label": "Plan",
    }
    assert tree.api.patch(tree.path, headers=who.headers, json=sent).status_code == 200
    assert tree.node(task["node_id"])["task"]["start"]["date"] == "2026-11-09"
    body = undone(tree, who)
    assert (body["undone"]["kind"], body["undone"]["node_ids"]) == ("structure_update", [])
    assert body["written"]["nodes"] == []
    assert tree.node(task["node_id"])["task"]["start"] == start
    listed = tree.api.get(tree.path.rsplit("/", 1)[0], headers=who.headers).json()
    structure = next(each for each in listed if each["structure_id"] == tree.structure_id)
    assert structure["label"] != "Plan"
    assert redone(tree, who)["undone"]["kind"] == "structure_update"
    assert tree.node(task["node_id"])["task"]["start"]["date"] == "2026-11-09"


# --- The refusals --------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undoing_of_a_change_another_contributor_took_up_since_names_the_object_in_conflict(
    tree: Tree, who: Person
) -> None:
    # Vérif : « L'annulation d'une modification qu'un autre contributeur a depuis reprise est
    # refusée en nommant l'objet en conflit. »
    task = tree.made("Câblage", who=who)
    assert tree.change(tree.node(task["node_id"]), who, label="Câblage du poste").status_code == 200
    assert tree.change(tree.node(task["node_id"]), None, label="Câblage repris").status_code == 200
    answer = undo(tree, who)
    assert refusal(answer) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": task["node_id"], "conflicting_object_label": "Câblage repris"},
    )
    assert tree.labels() == ["Câblage repris"]
    # Nothing is undone: the entry stays on the stack, and the redo has nothing to redo.
    assert refusal(redo(tree, who))[2] == {"missing_condition": "redo_history_not_empty"}


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_stack_with_nothing_to_undo_or_to_redo_is_refused_by_the_condition_it_misses(
    tree: Tree, who: Person
) -> None:
    assert refusal(undo(tree, who)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "undo_history_not_empty"},
    )
    assert refusal(redo(tree, who)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "redo_history_not_empty"},
    )


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_token_without_a_session_of_sign_in_has_no_history_to_undo_nor_to_redo(
    tree: Tree, stage: Scene
) -> None:
    # #2472 : refusé par un 403 nommé, sans paramètre ; une écriture faite avec ce jeton passe,
    # sans entrée d'historique.
    manager = stage.manager
    task = tree.made("Câblage")
    assert (
        tree.change(tree.node(task["node_id"]), manager, label="Câblage du poste").status_code
        == 200
    )
    assert entries(stage) == []
    for asked in (undo, redo):
        answer = asked(tree, manager)
        assert refusal(answer) == (403, "SESSION_ID_MISSING", {})
    assert tree.labels() == ["Câblage du poste"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_stack_belongs_to_its_account_and_its_session_of_sign_in(
    tree: Tree, stage: Scene, realm: TestRealm, who: Person
) -> None:
    other = signed_in(stage, realm)
    task = tree.made("Câblage", who=who)
    assert refusal(undo(tree, other))[2] == {"missing_condition": "undo_history_not_empty"}
    assert undone(tree, who)["undone"]["node_ids"] == [task["node_id"]]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undoing_on_a_revision_that_is_marked_or_unknown_is_refused(
    tree: Tree, stage: Scene, who: Person
) -> None:
    tree.made("Câblage", who=who)
    ghost = tree.api.post(
        f"{tree.path.split('/revisions/')[0]}/revisions/{uuid4()}/undo", headers=who.headers
    )
    assert refusal(ghost)[:2] == (404, "NOT_FOUND")
    mark(stage, tree.revision)
    assert refusal(undo(tree, who)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )


@pytest.mark.requirement("WF-ADM-0100-A")
def test_an_undoing_is_refused_for_the_permission_of_the_entry_the_caller_no_longer_holds(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # The state of a task is an entry of the remaining to commit (``remaining.write``), the others
    # of the planning (``planning.write``): refused 403, naming the permission; nothing is undone.
    task = tree.made("Câblage", who=who)
    assert tree.change(tree.node(task["node_id"]), who, label="Câblage du poste").status_code == 200
    held = ("planning.read", "planning.write")
    project, revision = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])

    def attempt(permissions: tuple[str, ...]) -> Any:
        act = Act(who.user_id, utc_now())
        with stage.database.transaction() as session:
            return undo_last_change(
                session, project, revision, writing.Writer(act, "office"), permissions
            )

    with pytest.raises(ForbiddenError) as refused:
        attempt(("planning.read",))
    assert (refused.value.code, dict(refused.value.params)) == (
        "PERMISSION_MISSING",
        {"missing_permission": "planning.write"},
    )
    assert tree.labels() == ["Câblage du poste"]
    assert attempt(held).kind == "cell"
    assert tree.labels() == ["Câblage"]
    # The state of a task is the remaining to commit's, entered while the project is in progress.
    put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    node = tree.node(task["node_id"])
    started = {"progress": "started", "lock_version": node["lock_version"]}
    answer = tree.api.put(
        f"{tree.path}/nodes/{task['node_id']}/progress", headers=who.headers, json=started
    )
    assert answer.status_code == 200, answer.text
    with pytest.raises(ForbiddenError) as refused:
        attempt(held)
    assert refused.value.params == {"missing_permission": "remaining.write"}
    assert attempt((*held, "remaining.write")).kind == "progress"
    assert tree.node(task["node_id"])["task"]["progress"] == "not_started"


# --- The lock of the structure ------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_lock_of_an_undoing_finds_the_structure_from_the_objects_of_a_creation_or_a_deletion(
    tree: Tree, who: Person, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #2476 : the structure is locked once, by the frame of the history alone, found from the
    # objects it names — ``expected`` alone to undo a creation, ``restored`` alone to undo a
    # deletion.
    locked: list[UUID] = []
    real = writing.structure_facts

    def spy(session: Any, project_id: UUID, structure_id: UUID, *, lock: bool) -> Any:
        if lock:
            locked.append(structure_id)
        return real(session, project_id, structure_id, lock=lock)

    monkeypatch.setattr(writing, "structure_facts", spy)
    task = tree.made("Câblage", who=who)
    locked.clear()
    undone(tree, who)
    assert tree.labels() == []
    # Once: the replay of the engine is handed the facts the frame read under the lock. The
    # creation undone: its entry holds the task after it and no object before it.
    assert locked == [UUID(tree.structure_id)]
    [creation] = entries(tree.stage)
    assert (creation.before, [each["object_id"] for each in creation.after]) == (
        [],
        [task["node_id"]],
    )


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_lock_of_a_redoing_and_of_an_undoing_of_a_deletion_find_the_structure_as_well(
    tree: Tree, who: Person, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = tree.made("Câblage", who=who)
    assert delete(tree, tree.node(task["node_id"]), who).status_code == 200
    locked: list[UUID] = []
    real = writing.structure_facts

    def spy(session: Any, project_id: UUID, structure_id: UUID, *, lock: bool) -> Any:
        if lock:
            locked.append(structure_id)
        return real(session, project_id, structure_id, lock=lock)

    monkeypatch.setattr(writing, "structure_facts", spy)
    # The deletion undone: its entry holds the task before it and no object after it.
    [creating, deleting] = entries(tree.stage)
    assert deleting.after == []
    undone(tree, who)
    redone(tree, who)
    assert creating.kind == "node_create"
    # Once each, by the frame alone: the replay of the engine is handed the facts it read.
    assert locked == [UUID(tree.structure_id)] * 2


@pytest.mark.requirement("WF-IHM-0110-A")
def test_two_undoings_of_one_stack_come_one_after_the_other(
    tree: Tree, who: Person, stage: Scene
) -> None:
    tree.made("Étude", who=who)
    tree.made("Travaux", who=who)

    def asked(_: int) -> int:
        return undo(tree, who).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(asked, range(2)))
    assert statuses == [200, 200]
    assert tree.labels() == []
    assert [each.undone for each in entries(stage)] == [True, True]


# --- What others hold since --------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_deletion_is_a_conflict_when_another_task_took_its_place(
    tree: Tree, who: Person
) -> None:
    first = tree.made("Étude", who=who)
    second = tree.made("Travaux", who=who)
    assert delete(tree, tree.node(second["node_id"]), who).status_code == 200
    taken = tree.made("Essais")
    answer = undo(tree, who)
    assert refusal(answer) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": taken["node_id"], "conflicting_object_label": "Essais"},
    )
    assert tree.labels() == ["Étude", "Essais"]
    assert tree.node(first["node_id"])["position"] == 1


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_creation_is_a_conflict_when_a_task_was_added_under_it_since(
    tree: Tree, who: Person
) -> None:
    summary = tree.made("Étude", who=who)
    child = tree.made("Note", parent_id=summary["node_id"])
    answer = undo(tree, who)
    assert refusal(answer) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": child["node_id"], "conflicting_object_label": "Note"},
    )
    assert tree.labels() == ["Étude", "Note"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_move_is_a_conflict_when_the_parent_it_comes_back_to_is_gone(
    tree: Tree, who: Person
) -> None:
    chantier = tree.made("Chantier", who=who)
    task = tree.made("Câblage", who=who, parent_id=chantier["node_id"])
    tree.made("Essais", who=who, parent_id=chantier["node_id"])
    body = {"node_ids": [task["node_id"]], "parent_id": None, "lock_version": counter(tree)}
    assert (
        tree.api.post(f"{tree.path}/nodes/move", headers=who.headers, json=body).status_code == 200
    )
    # The summary, which the move wrote nowhere, goes with its other subordinate.
    assert delete(tree, tree.node(chantier["node_id"]), tree.stage.manager).status_code == 200
    answer = undo(tree, who)
    assert refusal(answer) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": task["node_id"], "conflicting_object_label": "Câblage"},
    )
    assert tree.labels() == ["Câblage"]


# --- The work breakdown, gone since -----------------------------------------------------------


def attach(tree: Tree, node: dict[str, Any], who: Person, package: UUID | None) -> dict[str, Any]:
    """Attach a task to a work package, or take it away, at the counter read; give the node."""
    body = {"work_package_id": None if package is None else str(package)}
    answer = tree.change(tree.node(node["node_id"]), who, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()["nodes"][0]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_does_not_restore_the_attachment_to_an_element_that_no_longer_exists(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # #2501 : neutralised — the task comes back without the element, the rest as it was. A refusal
    # would have to be declared by the contract, and the undoing of a label must not fail for an
    # element it never touched.
    package, _ = work_breakdown(stage)
    task = tree.made("Câblage", who=who)
    attach(tree, task, who, package)
    assert tree.change(tree.node(task["node_id"]), who, label="Câblage du poste").status_code == 200
    # The element leaves the work breakdown, the tasks of the current revision lose it unwritten.
    with stage.owner.begin() as connection:
        connection.execute(
            update(Task).where(Task.node_id == UUID(task["node_id"])).values(work_package_id=None)
        )
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=utc_now())
        )
    body = undone(tree, who)
    assert body["undone"]["kind"] == "cell"
    read = tree.node(task["node_id"])["task"]
    assert (read["label"], read["work_package_id"]) == ("Câblage", None)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_redoing_does_not_restore_the_attachment_to_an_element_marked_deleted(
    tree: Tree, stage: Scene, who: Person
) -> None:
    package, _ = work_breakdown(stage)
    task = tree.made("Câblage", who=who)
    attach(tree, task, who, package)
    undone(tree, who)
    assert tree.node(task["node_id"])["task"]["work_package_id"] is None
    with stage.owner.begin() as connection:
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=utc_now())
        )
    body = redone(tree, who)
    assert body["undone"]["kind"] == "cell"
    assert tree.node(task["node_id"])["task"]["work_package_id"] is None


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_is_a_conflict_when_another_task_bears_the_element_it_would_give_back(
    tree: Tree, stage: Scene, who: Person
) -> None:
    package, _ = work_breakdown(stage)
    first = tree.made("Câblage", who=who)
    second = tree.made("Essais", who=who)
    attach(tree, first, who, package)
    attach(tree, first, who, None)
    answer = tree.change(tree.node(second["node_id"]), None, work_package_id=str(package))
    assert answer.status_code == 200, answer.text
    refused = undo(tree, who)
    assert refusal(refused) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": second["node_id"], "conflicting_object_label": "Essais"},
    )


# --- What the objects of an entry hold, gone or changed since ----------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_deletion_gives_back_a_whole_subtree_parents_before_children(
    tree: Tree, who: Person
) -> None:
    project = tree.made("Projet", who=who)
    study = tree.made("Études", who=who, parent_id=project["node_id"])
    note = tree.made("Note", who=who, parent_id=study["node_id"])
    works = tree.made("Travaux", who=who, parent_id=project["node_id"])
    before = [(each["node_id"], each["parent_id"], each["row_number"]) for each in tree.items()]
    assert delete(tree, tree.node(study["node_id"]), who).status_code == 200
    assert tree.labels() == ["Projet", "Travaux"]
    body = undone(tree, who)
    assert sorted(each["node_id"] for each in body["written"]["nodes"]) == sorted(
        [study["node_id"], note["node_id"]]
    )
    assert [each["node_id"] for each in body["written"]["ancestors"]] == [project["node_id"]]
    after = [(each["node_id"], each["parent_id"], each["row_number"]) for each in tree.items()]
    assert after == before
    assert tree.node(works["node_id"])["parent_id"] == project["node_id"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_deletion_leaves_out_a_link_whose_other_end_is_gone_and_a_dead_timeline(
    tree: Tree, stage: Scene, who: Person
) -> None:
    design = tree.made("Étude", who=who)
    works = tree.made("Travaux", who=who)
    assert link(tree, tree.node(works["node_id"]), who, design).status_code == 200
    timeline = uuid4()
    element = {"project_id": UUID(stage.project["project_id"]), **STAMP}
    with stage.owner.begin() as connection:
        connection.execute(insert(Timeline).values(id=timeline, label="Jalons", **element))
        connection.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                lineage_id=UUID(works["lineage_id"]),
                kind="timeline",
                timeline_id=timeline,
                **element,
            )
        )
    assert delete(tree, tree.node(works["node_id"]), who).status_code == 200
    # The study goes, and the timeline, while the task is gone.
    assert delete(tree, tree.node(design["node_id"]), stage.manager).status_code == 200
    with stage.owner.begin() as connection:
        connection.execute(delete_rows(Timeline).where(Timeline.id == timeline))
    undone(tree, who)
    assert tree.labels() == ["Travaux"]
    assert tree.node(works["node_id"])["predecessors"] == []
    assert rows(stage, TaskLink) == 0
    assert rows(stage, TrackingEntry) == 0


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_change_of_predecessors_brings_back_the_type_and_the_lag_of_the_link(
    tree: Tree, who: Person
) -> None:
    design = tree.made("Étude", who=who)
    works = tree.made("Travaux", who=who)
    assert link(tree, tree.node(works["node_id"]), who, design).status_code == 200
    [first] = tree.node(works["node_id"])["predecessors"]
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": design["node_id"],
                "link_type": "start_to_start",
                "lag": {"value": "2", "unit": "d"},
            }
        ],
        "lock_version": tree.node(works["node_id"])["lock_version"],
    }
    path = f"{tree.path}/nodes/{works['node_id']}/predecessors"
    assert tree.api.put(path, headers=who.headers, json=sent).status_code == 200
    assert tree.node(works["node_id"])["predecessors"][0]["lag"] == {"value": "2", "unit": "d"}
    undone(tree, who)
    [restored] = tree.node(works["node_id"])["predecessors"]
    assert restored == first


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_tracking_takes_back_the_inscriptions_of_the_task_it_wrote(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # The inscriptions are written by US-1400/L2; an entry of their kind is framed here as that
    # story will, around the service, to prove what the restitution does of it.
    task = tree.made("Jalon", who=who)
    node_id = UUID(task["node_id"])
    project, revision = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    stack = UndoStack(revision, who.user_id, SESSION)
    change = RecordedChange(project, stack, "tracking", (node_id,), utc_now())
    with stage.database.transaction() as session, recording(session, change) as frame:
        frame.keep_before(snapshot(session, project, (node_id,)))
        now = utc_now()
        session.add(
            TrackingEntry(
                id=uuid4(),
                project_id=project,
                lineage_id=UUID(task["lineage_id"]),
                kind="milestone_tracking",
                timeline_id=None,
                created_at=now,
                created_by=who.user_id,
                updated_at=now,
                updated_by=who.user_id,
            )
        )
        session.flush()
        session.get_one(Node, (project, node_id)).lock_version += 1
        frame.keep_after(snapshot(session, project, (node_id,)))
    assert rows(stage, TrackingEntry) == 1
    assert undone(tree, who)["undone"]["kind"] == "tracking"
    assert rows(stage, TrackingEntry) == 0
    assert redone(tree, who)["undone"]["kind"] == "tracking"
    assert rows(stage, TrackingEntry) == 1
